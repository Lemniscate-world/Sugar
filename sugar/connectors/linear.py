# Copyright (c) 2026 kuro. All Rights Reserved.
"""Linear connector — read and write to Linear via GraphQL API."""

from __future__ import annotations

import logging

import requests

from sugar.connectors.base import ActionResult, BaseConnector

logger = logging.getLogger(__name__)

LINEAR_API_URL = "https://api.linear.app/graphql"


class LinearConnector(BaseConnector):
    """Connector for Linear project management.

    Supports: listing issues, creating issues, updating issues, searching,
    and listing projects/teams.
    """

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    @property
    def name(self) -> str:
        return "linear"

    @property
    def description(self) -> str:
        return (
            "Linear project management. Use this to manage issues, projects, "
            "and track progress on tasks."
        )

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def available_actions(self) -> list[dict[str, str]]:
        return [
            {
                "name": "list_issues",
                "description": "List recent issues, optionally filtered by state or assignee",
                "params": "state (optional: 'backlog','todo','in_progress','done'), "
                "limit (optional, default 10)",
            },
            {
                "name": "search_issues",
                "description": "Search issues by text query",
                "params": "query (required: search text), limit (optional, default 10)",
            },
            {
                "name": "create_issue",
                "description": "Create a new issue in Linear",
                "params": "title (required), description (optional), "
                "team_id (optional, uses first team if not specified), "
                "priority (optional: 0=none, 1=urgent, 2=high, 3=medium, 4=low)",
            },
            {
                "name": "update_issue",
                "description": "Update an existing issue",
                "params": "issue_id (required), title (optional), description (optional), "
                "state_name (optional: set status like 'Done', 'In Progress')",
            },
            {
                "name": "list_projects",
                "description": "List all projects",
                "params": "limit (optional, default 20)",
            },
            {
                "name": "list_teams",
                "description": "List all teams",
                "params": "(none)",
            },
        ]

    def execute(self, action: str, params: dict) -> ActionResult:
        """Route to the appropriate action handler."""
        handlers = {
            "list_issues": self._list_issues,
            "search_issues": self._search_issues,
            "create_issue": self._create_issue,
            "update_issue": self._update_issue,
            "list_projects": self._list_projects,
            "list_teams": self._list_teams,
        }
        handler = handlers.get(action)
        if not handler:
            return ActionResult(success=False, data=f"Unknown action: {action}")
        try:
            return handler(params)
        except Exception as e:
            logger.error("Linear %s failed: %s", action, e)
            return ActionResult(success=False, data=f"Error: {e}")

    def _graphql(self, query: str, variables: dict | None = None) -> dict:
        """Execute a GraphQL query against Linear API."""
        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
        }
        payload: dict = {"query": query}
        if variables:
            payload["variables"] = variables

        response = requests.post(LINEAR_API_URL, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()

        if "errors" in result:
            raise RuntimeError(f"GraphQL errors: {result['errors']}")

        return result.get("data", {})

    def _list_issues(self, params: dict) -> ActionResult:
        limit = params.get("limit", 10)
        state_filter = params.get("state", "")

        # Build filter
        filter_clause = ""
        if state_filter:
            state_map = {
                "backlog": "Backlog",
                "todo": "Todo",
                "in_progress": "In Progress",
                "done": "Done",
            }
            state_name = state_map.get(state_filter.lower(), state_filter)
            filter_clause = f', filter: {{state: {{name: {{eq: "{state_name}"}}}}}}' 

        query = f"""
        query {{
            issues(first: {limit}{filter_clause}, orderBy: updatedAt) {{
                nodes {{
                    id
                    identifier
                    title
                    state {{ name }}
                    priority
                    assignee {{ name }}
                    updatedAt
                }}
            }}
        }}
        """
        data = self._graphql(query)
        issues = data.get("issues", {}).get("nodes", [])

        if not issues:
            return ActionResult(success=True, data="No issues found.", raw=issues)

        lines = []
        for issue in issues:
            assignee = issue.get("assignee", {})
            assignee_name = assignee.get("name", "Unassigned") if assignee else "Unassigned"
            state = issue.get("state", {}).get("name", "Unknown")
            lines.append(
                f"- **{issue['identifier']}**: {issue['title']} "
                f"[{state}] (Assignee: {assignee_name})"
            )

        return ActionResult(
            success=True,
            data=f"Found {len(issues)} issues:\n" + "\n".join(lines),
            raw=issues,
        )

    def _search_issues(self, params: dict) -> ActionResult:
        query_text = params.get("query", "")
        limit = params.get("limit", 10)

        if not query_text:
            return ActionResult(success=False, data="Missing 'query' parameter.")

        query = f"""
        query {{
            issueSearch(query: "{query_text}", first: {limit}) {{
                nodes {{
                    id
                    identifier
                    title
                    state {{ name }}
                    assignee {{ name }}
                    description
                }}
            }}
        }}
        """
        data = self._graphql(query)
        issues = data.get("issueSearch", {}).get("nodes", [])

        if not issues:
            return ActionResult(success=True, data=f"No issues found for '{query_text}'.")

        lines = []
        for issue in issues:
            assignee = issue.get("assignee", {})
            assignee_name = assignee.get("name", "Unassigned") if assignee else "Unassigned"
            state = issue.get("state", {}).get("name", "Unknown")
            desc = (issue.get("description") or "")[:80]
            lines.append(
                f"- **{issue['identifier']}**: {issue['title']} [{state}] "
                f"({assignee_name}) — {desc}"
            )

        return ActionResult(
            success=True,
            data=f"Found {len(issues)} issues matching '{query_text}':\n" + "\n".join(lines),
            raw=issues,
        )

    def _create_issue(self, params: dict) -> ActionResult:
        title = params.get("title", "")
        if not title:
            return ActionResult(success=False, data="Missing 'title' parameter.")

        description = params.get("description", "")
        priority = params.get("priority", 0)
        team_id = params.get("team_id", "")

        # If no team_id, get the first team
        if not team_id:
            teams_data = self._graphql("query { teams { nodes { id name } } }")
            teams = teams_data.get("teams", {}).get("nodes", [])
            if not teams:
                return ActionResult(success=False, data="No teams found in Linear.")
            team_id = teams[0]["id"]

        mutation = """
        mutation CreateIssue($input: IssueCreateInput!) {
            issueCreate(input: $input) {
                success
                issue {
                    id
                    identifier
                    title
                    url
                }
            }
        }
        """
        variables = {
            "input": {
                "title": title,
                "description": description,
                "teamId": team_id,
                "priority": priority,
            }
        }
        data = self._graphql(mutation, variables)
        result = data.get("issueCreate", {})

        if result.get("success"):
            issue = result.get("issue", {})
            return ActionResult(
                success=True,
                data=f"✅ Created issue **{issue.get('identifier')}**: {issue.get('title')}\n"
                f"URL: {issue.get('url', 'N/A')}",
                raw=issue,
            )
        return ActionResult(success=False, data="Failed to create issue.")

    def _update_issue(self, params: dict) -> ActionResult:
        issue_id = params.get("issue_id", "")
        if not issue_id:
            return ActionResult(success=False, data="Missing 'issue_id' parameter.")

        update_fields: dict = {}
        if "title" in params:
            update_fields["title"] = params["title"]
        if "description" in params:
            update_fields["description"] = params["description"]
        if "state_name" in params:
            # Resolve state name to ID
            state_name = params["state_name"]
            states_data = self._graphql("""
                query { workflowStates { nodes { id name } } }
            """)
            states = states_data.get("workflowStates", {}).get("nodes", [])
            state_match = next(
                (s for s in states if s["name"].lower() == state_name.lower()), None
            )
            if state_match:
                update_fields["stateId"] = state_match["id"]
            else:
                available = [s["name"] for s in states]
                return ActionResult(
                    success=False,
                    data=f"State '{state_name}' not found. Available: {available}",
                )

        if not update_fields:
            return ActionResult(success=False, data="No fields to update.")

        mutation = """
        mutation UpdateIssue($id: String!, $input: IssueUpdateInput!) {
            issueUpdate(id: $id, input: $input) {
                success
                issue { identifier title state { name } }
            }
        }
        """
        data = self._graphql(mutation, {"id": issue_id, "input": update_fields})
        result = data.get("issueUpdate", {})

        if result.get("success"):
            issue = result.get("issue", {})
            return ActionResult(
                success=True,
                data=f"✅ Updated **{issue.get('identifier')}**: {issue.get('title')} "
                f"[{issue.get('state', {}).get('name', '')}]",
                raw=issue,
            )
        return ActionResult(success=False, data="Failed to update issue.")

    def _list_projects(self, params: dict) -> ActionResult:
        limit = params.get("limit", 20)
        query = f"""
        query {{
            projects(first: {limit}) {{
                nodes {{
                    id
                    name
                    state
                    progress
                    startDate
                    targetDate
                }}
            }}
        }}
        """
        data = self._graphql(query)
        projects = data.get("projects", {}).get("nodes", [])

        if not projects:
            return ActionResult(success=True, data="No projects found.")

        lines = []
        for p in projects:
            progress = int((p.get("progress") or 0) * 100)
            lines.append(
                f"- **{p['name']}** [{p.get('state', 'N/A')}] — {progress}% complete"
            )

        return ActionResult(
            success=True,
            data=f"Found {len(projects)} projects:\n" + "\n".join(lines),
            raw=projects,
        )

    def _list_teams(self, params: dict) -> ActionResult:
        data = self._graphql("query { teams { nodes { id name key } } }")
        teams = data.get("teams", {}).get("nodes", [])

        if not teams:
            return ActionResult(success=True, data="No teams found.")

        lines = [f"- **{t['name']}** (key: {t['key']})" for t in teams]
        return ActionResult(
            success=True,
            data=f"Found {len(teams)} teams:\n" + "\n".join(lines),
            raw=teams,
        )
