import React, { useState, useEffect } from 'react';
import SugarLogo from './SugarLogo';
import { Home, Folder, MessageSquare, Settings, Plus, MessageCircle } from 'lucide-react';
import clsx from 'clsx';

export default function Sidebar({ onNewChat, onSelectChat, activeConversationId }) {
    const [conversations, setConversations] = useState([]);

    const fetchConversations = () => {
        fetch('/api/conversations')
            .then(r => r.json())
            .then(data => setConversations(data.conversations || []))
            .catch(console.error);
    };

    useEffect(() => {
        fetchConversations();
        // Poll for updates every 5s? Or just rely on props
        const interval = setInterval(fetchConversations, 5000);
        return () => clearInterval(interval);
    }, [activeConversationId]);

    return (
        <div className="w-64 bg-gray-950 border-r border-gray-800 flex flex-col p-4">
            {/* Branding */}
            <div className="flex items-center gap-3 mb-8 px-2">
                <SugarLogo className="w-8 h-8" />
                <span className="text-xl font-bold bg-gradient-to-r from-sugar-200 to-sugar-600 bg-clip-text text-transparent">
                    Sugar
                </span>
            </div>

            {/* New Chat */}
            <button
                onClick={onNewChat}
                className="flex items-center gap-2 w-full bg-sugar-600 hover:bg-sugar-500 text-white px-4 py-2 rounded-lg mb-6 transition-colors font-medium text-sm"
            >
                <Plus className="w-4 h-4" />
                New Chat
            </button>

            {/* Navigation */}
            <div className="space-y-6 flex-1 overflow-y-auto scrollbar-hide">
                <div>
                    <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 px-2">Recent Chats</h3>
                    <div className="space-y-1">
                        {conversations.map(conv => (
                            <button
                                key={conv.id}
                                onClick={() => onSelectChat(conv.id)}
                                className={clsx(
                                    "w-full text-left px-3 py-2 rounded-lg text-sm truncate transition-colors flex items-center gap-2",
                                    activeConversationId === conv.id ? "bg-gray-800 text-white" : "text-gray-400 hover:text-gray-300 hover:bg-gray-900"
                                )}
                            >
                                <MessageCircle className="w-4 h-4 flex-shrink-0 opacity-50" />
                                <span className="truncate">{conv.title || "New Chat"}</span>
                            </button>
                        ))}
                        {conversations.length === 0 && (
                            <p className="text-xs text-gray-600 px-3 italic">No recent chats</p>
                        )}
                    </div>
                </div>
            </div>

            {/* Footer */}
            <div className="border-t border-gray-800 pt-4 text-xs text-gray-500 px-2 flex justify-between">
                <span>Sugar v0.3.0</span>
                <Settings className="w-4 h-4 hover:text-white cursor-pointer" />
            </div>
        </div>
    );
}
