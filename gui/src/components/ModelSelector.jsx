import React, { useState, useEffect, useRef } from 'react';
import { ChevronDown, Download, Loader2, Check, X } from 'lucide-react';
import clsx from 'clsx';

export default function ModelSelector({ currentModel, onSelect }) {
    const [models, setModels] = useState([]);
    const [isOpen, setIsOpen] = useState(false);
    const [showPull, setShowPull] = useState(false);
    const [pullName, setPullName] = useState("");
    const [isPulling, setIsPulling] = useState(false);
    const [pullProgress, setPullProgress] = useState(null);
    const dropdownRef = useRef(null);

    useEffect(() => {
        fetch('/api/ollama/models')
            .then(r => r.json())
            .then(data => setModels(data.models || []))
            .catch(console.error);
    }, [isPulling]); // Refresh list after pull

    useEffect(() => {
        function handleClickOutside(event) {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setIsOpen(false);
                setShowPull(false);
            }
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    const handlePull = async (e) => {
        e.preventDefault();
        if (!pullName.trim()) return;

        setIsPulling(true);
        setPullProgress("Starting download...");

        try {
            const response = await fetch('/api/models/pull', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: pullName })
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6);
                        if (data === '[DONE]') break;
                        try {
                            const status = JSON.parse(data);
                            if (status.status) setPullProgress(status.status);
                            if (status.completed && status.total) {
                                const percent = Math.round((status.completed / status.total) * 100);
                                setPullProgress(`${status.status} (${percent}%)`);
                            }
                        } catch (e) { console.error(e) }
                    }
                }
            }

            // Success
            setPullProgress("Done!");
            setTimeout(() => {
                setIsPulling(false);
                setPullProgress(null);
                setShowPull(false);
                setPullName("");
                onSelect(pullName.includes(':') ? pullName : `${pullName}:latest`);
            }, 1000);

        } catch (e) {
            setPullProgress(`Error: ${e.message}`);
            setTimeout(() => setIsPulling(false), 3000);
        }
    };

    return (
        <div className="relative" ref={dropdownRef}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center gap-2 px-3 py-1.5 bg-gray-900 border border-gray-800 rounded-lg hover:border-gray-700 transition-colors text-sm text-gray-300"
            >
                <div className="w-2 h-2 rounded-full bg-green-500"></div>
                <span className="font-mono">{currentModel}</span>
                <ChevronDown className="w-4 h-4 text-gray-500" />
            </button>

            {isOpen && (
                <div className="absolute top-full right-0 mt-2 w-64 bg-gray-900 border border-gray-800 rounded-xl shadow-xl shadow-black/50 overflow-hidden z-50">
                    {!showPull ? (
                        <>
                            <div className="max-h-60 overflow-y-auto py-1">
                                {models.map(model => (
                                    <button
                                        key={model}
                                        onClick={() => { onSelect(model); setIsOpen(false); }}
                                        className={clsx(
                                            "w-full text-left px-4 py-2 text-sm hover:bg-gray-800 flex items-center justify-between group",
                                            currentModel === model ? "text-sugar-400 bg-sugar-900/10" : "text-gray-400"
                                        )}
                                    >
                                        {model}
                                        {currentModel === model && <Check className="w-3 h-3" />}
                                    </button>
                                ))}
                            </div>
                            <div className="border-t border-gray-800 p-2">
                                <button
                                    onClick={() => setShowPull(true)}
                                    className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-xs font-medium text-gray-300 transition-colors"
                                >
                                    <Download className="w-3 h-3" />
                                    Pull New Model
                                </button>
                            </div>
                        </>
                    ) : (
                        <div className="p-4">
                            <div className="flex items-center justify-between mb-3 text-sm text-gray-400">
                                <span>Pull from Library</span>
                                {!isPulling && (
                                    <button onClick={() => setShowPull(false)}><X className="w-4 h-4 hover:text-white" /></button>
                                )}
                            </div>

                            <form onSubmit={handlePull} className="space-y-3">
                                <input
                                    type="text"
                                    value={pullName}
                                    onChange={(e) => setPullName(e.target.value)}
                                    placeholder="e.g. llama3, mistral"
                                    className="w-full bg-gray-950 border border-gray-800 rounded px-3 py-2 text-sm text-white focus:ring-1 focus:ring-sugar-500 outline-none"
                                    disabled={isPulling}
                                    autoFocus
                                />

                                {isPulling ? (
                                    <div className="bg-gray-800 rounded px-3 py-2 text-xs text-sugar-300 flex items-center gap-2">
                                        <Loader2 className="w-3 h-3 animate-spin flex-shrink-0" />
                                        <span className="truncate">{pullProgress || "Connecting..."}</span>
                                    </div>
                                ) : (
                                    <button
                                        type="submit"
                                        disabled={!pullName.trim()}
                                        className="w-full btn-primary py-1.5 text-xs"
                                    >
                                        Pull Model
                                    </button>
                                )}
                            </form>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
