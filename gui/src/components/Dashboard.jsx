import React from 'react';
import Chat from './Chat';
import Sidebar from './Sidebar';
import ModelSelector from './ModelSelector';

export default function Dashboard({ config, updateConfig }) {
    const handleModelSelect = (model) => {
        updateConfig('ollama_model', model);
        // Persist to backend
        fetch('/api/config/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ...config, ollama_model: model })
        }).catch(console.error);
    };

    return (
        <div className="flex h-screen bg-gray-950 text-white overflow-hidden">
            <Sidebar />
            <main className="flex-1 p-4 flex flex-col min-w-0">
                <header className="flex justify-between items-center mb-4 px-2">
                    <h1 className="text-xl font-semibold">Chat</h1>
                    <ModelSelector
                        currentModel={config.ollama_model}
                        onSelect={handleModelSelect}
                    />
                </header>
                <div className="flex-1 min-h-0">
                    <Chat config={config} />
                </div>
            </main>
        </div>
    )
}
