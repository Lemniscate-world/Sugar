import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Send, Loader2, User, Bot } from 'lucide-react';
import clsx from 'clsx';

export default function Chat({ config, conversationId, onConversationCreated }) {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(scrollToBottom, [messages]);

    // Load history when conversationId changes
    useEffect(() => {
        if (conversationId) {
            setIsLoading(true);
            fetch(`/api/conversations/${conversationId}`)
                .then(r => r.json())
                .then(data => {
                    setMessages(data.messages || []);
                    setIsLoading(false);
                })
                .catch(e => {
                    console.error(e);
                    setIsLoading(false);
                });
        } else {
            setMessages([]);
        }
    }, [conversationId]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!input.trim() || isLoading) return;

        const userMsg = input.trim();
        setInput("");

        // Optimistic update
        const newMessages = [...messages, { role: 'user', content: userMsg }];
        setMessages(newMessages);
        setIsLoading(true);

        try {
            const response = await fetch('/api/chat/stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    messages: newMessages,
                    model: config.ollama_model,
                    conversation_id: conversationId
                })
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let botMsg = { role: 'assistant', content: '' };

            setMessages(prev => [...prev, botMsg]);

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
                            const parsed = JSON.parse(data);

                            if (parsed.conversation_id) {
                                if (onConversationCreated && !conversationId) {
                                    onConversationCreated(parsed.conversation_id);
                                }
                                continue;
                            }

                            if (parsed.content) {
                                botMsg.content += parsed.content;
                                setMessages(prev => {
                                    const newMsgs = [...prev];
                                    newMsgs[newMsgs.length - 1] = { ...botMsg };
                                    return newMsgs;
                                });
                            }

                            if (parsed.error) {
                                setMessages(prev => [...prev, { role: 'system', content: `Error: ${parsed.error}` }]);
                            }
                        } catch (e) {
                            console.error('Error parsing chunk', e);
                        }
                    }
                }
            }
        } catch (error) {
            console.error('Chat error:', error);
            setMessages(prev => [...prev, { role: 'system', content: `Error: ${error.message}` }]);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="flex flex-col h-full bg-gray-900 rounded-xl overflow-hidden border border-gray-800">
            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-6 scrollbar-thin scrollbar-thumb-gray-700">
                {messages.length === 0 && (
                    <div className="text-center text-gray-500 mt-20">
                        <Bot className="w-12 h-12 mx-auto mb-4 opacity-50" />
                        <p className="text-lg">How can I help you today?</p>
                    </div>
                )}

                {messages.map((msg, idx) => (
                    <div key={idx} className={clsx("flex gap-4", msg.role === 'user' ? "flex-row-reverse" : "")}>
                        <div className={clsx(
                            "w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0",
                            msg.role === 'user' ? "bg-sugar-600" : "bg-gray-700"
                        )}>
                            {msg.role === 'user' ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
                        </div>

                        <div className={clsx(
                            "max-w-[80%] rounded-lg p-3 prose prose-invert prose-sm",
                            msg.role === 'user' ? "bg-sugar-900/30 border border-sugar-800" : "bg-gray-800/50 border border-gray-700"
                        )}>
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                {msg.content}
                            </ReactMarkdown>
                        </div>
                    </div>
                ))}
                <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="p-4 bg-gray-900 border-t border-gray-800">
                <form onSubmit={handleSubmit} className="relative">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder={`Message ${config.ollama_model}...`}
                        className="w-full bg-gray-950 text-white rounded-lg pl-4 pr-12 py-3 focus:outline-none focus:ring-2 focus:ring-sugar-500 border border-gray-800"
                        disabled={isLoading}
                    />
                    <button
                        type="submit"
                        disabled={!input.trim() || isLoading}
                        className="absolute right-2 top-1/2 -translate-y-1/2 p-2 text-sugar-400 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                        {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
                    </button>
                </form>
            </div>
        </div>
    );
}
