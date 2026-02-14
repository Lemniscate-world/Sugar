import React, { useState } from 'react';
import Chat from './Chat';
import Sidebar from './Sidebar';
import ModelSelector from './ModelSelector';

export default function Dashboard({ config, updateConfig }) {
    const [activeConversationId, setActiveConversationId] = useState(null);

    const handleModelSelect = (model) => {
        updateConfig('ollama_model', model);
        fetch('/api/config/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ...config, ollama_model: model })
        }).catch(console.error);
    };

    const handleNewChat = () => {
        setActiveConversationId(null);
    };

    const handleSelectChat = (id) => {
        setActiveConversationId(id);
    };

    const handleConversationCreated = (id) => {
        setActiveConversationId(id);
    };

    return (
        <div className="flex h-screen bg-gray-950 text-white overflow-hidden">
            <Sidebar
                onNewChat={handleNewChat}
                onSelectChat={handleSelectChat}
                activeConversationId={activeConversationId}
            />
            <main className="flex-1 p-4 flex flex-col min-w-0">
                <header className="flex justify-between items-center mb-4 px-2">
                    <h1 className="text-xl font-semibold">
                        {activeConversationId ? "Chat" : "New Chat"}
                    </h1>
                    <ModelSelector
                        currentModel={config.ollama_model}
                        onSelect={handleModelSelect}
                    />
                </header>
                <div className="flex-1 min-h-0">
                    <Chat
                        config={config}
                        conversationId={activeConversationId}
                        onConversationCreated={handleConversationCreated}
                    />
                </div>
            </main>
        </div>
    )
}
