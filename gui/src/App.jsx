import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronRight, Check, AlertCircle, Folder, Key, Terminal } from 'lucide-react'
import clsx from 'clsx'
import Dashboard from './components/Dashboard'
import SugarLogo from './components/SugarLogo'

// --- Setup Components ---

function WelcomeStep({ onNext }) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="text-center space-y-8 py-10"
        >
            <div className="relative inline-block">
                <div className="absolute inset-0 bg-sugar-500 blur-3xl opacity-20 rounded-full"></div>
                <SugarLogo className="w-24 h-24 relative z-10 mx-auto" />
            </div>

            <div className="space-y-2">
                <h1 className="text-5xl font-bold bg-gradient-to-r from-sugar-200 to-sugar-600 bg-clip-text text-transparent">
                    Sugar
                </h1>
                <p className="text-xl text-gray-400">Your personal AI operating layer.</p>
            </div>

            <div className="max-w-md mx-auto text-gray-400 text-sm bg-gray-900/50 p-6 rounded-xl border border-gray-800 backdrop-blur-sm">
                <p>We'll set up your local environment in 3 simple steps:</p>
                <ul className="mt-4 space-y-2 text-left">
                    <li className="flex items-center gap-2"><Folder className="w-4 h-4 text-sugar-500" /> Connect Obsidian Vault</li>
                    <li className="flex items-center gap-2"><Key className="w-4 h-4 text-sugar-500" /> Configure Linear (Optional)</li>
                    <li className="flex items-center gap-2"><Terminal className="w-4 h-4 text-sugar-500" /> Check Ollama Status</li>
                </ul>
            </div>

            <button onClick={onNext} className="btn-primary group">
                Get Started
                <ChevronRight className="w-5 h-5 inline-block ml-1 group-hover:translate-x-1 transition-transform" />
            </button>
        </motion.div>
    )
}

function VaultStep({ config, updateConfig, onNext, onBack }) {
    const [path, setPath] = useState(config.obsidian_vault_path || '')
    const [status, setStatus] = useState(null)
    const [isValidating, setIsValidating] = useState(false)

    const validate = async () => {
        setIsValidating(true)
        try {
            const res = await fetch('/api/validate/vault', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path })
            })
            const data = await res.json()
            if (data.valid) {
                setStatus({ valid: true, message: `Found ${data.md_count} notes`, is_obsidian: data.is_obsidian_vault })
                updateConfig('obsidian_vault_path', data.path)
            } else {
                setStatus({ valid: false, message: 'Invalid directory path' })
            }
        } catch (e) {
            setStatus({ valid: false, message: 'Validation failed' })
        }
        setIsValidating(false)
    }

    return (
        <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="step-content"
        >
            <div className="text-center mb-8">
                <div className="w-12 h-12 bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Folder className="w-6 h-6 text-sugar-400" />
                </div>
                <h2 className="text-2xl font-bold">Connect Obsidian</h2>
                <p className="text-gray-400 mt-2">Sugar needs access to your notes to read and write.</p>
            </div>

            <div className="space-y-4">
                <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Vault Path</label>
                    <div className="flex gap-2">
                        <input
                            type="text"
                            value={path}
                            onChange={(e) => setPath(e.target.value)}
                            placeholder="/home/user/Documents/MyVault"
                            className="input-field"
                        />
                        <button
                            onClick={validate}
                            disabled={isValidating || !path}
                            className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm font-medium transition-colors"
                        >
                            Check
                        </button>
                    </div>
                    {status && (
                        <div className={clsx("mt-3 flex items-center gap-2 text-sm", status.valid ? "text-green-400" : "text-red-400")}>
                            {status.valid ? <Check className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
                            {status.message}
                            {status.is_obsidian && <span className="bg-purple-900/50 text-purple-200 text-xs px-2 py-0.5 rounded ml-2">Obsidian Detected</span>}
                        </div>
                    )}
                </div>
            </div>

            <div className="flex justify-between pt-8">
                <button onClick={onBack} className="text-gray-400 hover:text-white transition-colors">Back</button>
                <button
                    onClick={onNext}
                    disabled={!status?.valid}
                    className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    Next Step
                </button>
            </div>
        </motion.div>
    )
}

function LinearStep({ config, updateConfig, onNext, onBack }) {
    const [key, setKey] = useState(config.linear_api_key || '')
    const [status, setStatus] = useState(null)
    const [isValidating, setIsValidating] = useState(false)

    const validate = async () => {
        setIsValidating(true)
        try {
            const res = await fetch('/api/validate/linear', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: key })
            })
            const data = await res.json()
            if (data.valid) {
                setStatus({ valid: true, message: `Connected as ${data.user}` })
                updateConfig('linear_api_key', key)
            } else {
                setStatus({ valid: false, message: data.error || 'Invalid API Key' })
            }
        } catch (e) {
            setStatus({ valid: false, message: 'Connection failed' })
        }
        setIsValidating(false)
    }

    const skip = () => {
        updateConfig('linear_api_key', '')
        onNext()
    }

    return (
        <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="step-content"
        >
            <div className="text-center mb-8">
                <div className="w-12 h-12 bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Key className="w-6 h-6 text-sugar-400" />
                </div>
                <h2 className="text-2xl font-bold">Connect Linear</h2>
                <p className="text-gray-400 mt-2">Optional. Allows Sugar to read and modify issues.</p>
            </div>

            <div className="space-y-4">
                <div className="bg-gray-900/50 p-4 rounded-lg border border-gray-800 text-sm text-gray-400 mb-6">
                    <p>Get your Personal API Key from <span className="text-white font-mono">Settings &gt; API &gt; Personal API Keys</span> in Linear.</p>
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">API Key</label>
                    <div className="flex gap-2">
                        <input
                            type="password"
                            value={key}
                            onChange={(e) => setKey(e.target.value)}
                            placeholder="lin_api_..."
                            className="input-field"
                        />
                        <button
                            onClick={validate}
                            disabled={isValidating || !key}
                            className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm font-medium transition-colors"
                        >
                            Verify
                        </button>
                    </div>
                    {status && (
                        <div className={clsx("mt-3 flex items-center gap-2 text-sm", status.valid ? "text-green-400" : "text-red-400")}>
                            {status.valid ? <Check className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
                            {status.message}
                        </div>
                    )}
                </div>
            </div>

            <div className="flex justify-between pt-8">
                <button onClick={onBack} className="text-gray-400 hover:text-white transition-colors">Back</button>
                <div className="space-x-4">
                    <button onClick={skip} className="text-gray-400 hover:text-white text-sm">Skip for now</button>
                    <button
                        onClick={onNext}
                        disabled={key && !status?.valid}
                        className="btn-primary"
                    >
                        Next Step
                    </button>
                </div>
            </div>
        </motion.div>
    )
}

function OllamaStep({ config, updateConfig, onNext, onBack }) {
    const [status, setStatus] = useState({ installed: false, running: false, models: [] })
    const [isLoading, setIsLoading] = useState(true)

    const checkStatus = async () => {
        setIsLoading(true)
        try {
            const res = await fetch('/api/status')
            const data = await res.json()
            setStatus(data.ollama)
            if (data.ollama.running && data.ollama.models.length > 0) {
                if (!config.ollama_model) {
                    updateConfig('ollama_model', data.ollama.models[0])
                }
            }
        } catch (e) {
            console.error(e)
        }
        setIsLoading(false)
    }

    useEffect(() => {
        checkStatus()
    }, [])

    return (
        <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="step-content"
        >
            <div className="text-center mb-8">
                <div className="w-12 h-12 bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Terminal className="w-6 h-6 text-sugar-400" />
                </div>
                <h2 className="text-2xl font-bold">System Check</h2>
                <p className="text-gray-400 mt-2">Sugar runs locally on Ollama.</p>
            </div>

            <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden divide-y divide-gray-800">
                <div className="p-4 flex items-center justify-between">
                    <span className="text-gray-300">Ollama Installed</span>
                    {isLoading ? <span className="text-gray-500">Checking...</span> :
                        status.installed ? <span className="text-green-400 flex items-center gap-1"><Check className="w-4 h-4" /> Yes</span> :
                            <span className="text-red-400 flex items-center gap-1"><AlertCircle className="w-4 h-4" /> No</span>
                    }
                </div>
                <div className="p-4 flex items-center justify-between">
                    <span className="text-gray-300">Service Running</span>
                    {isLoading ? <span className="text-gray-500">Checking...</span> :
                        status.running ? <span className="text-green-400 flex items-center gap-1"><Check className="w-4 h-4" /> Yes</span> :
                            <span className="text-red-400 flex items-center gap-1"><AlertCircle className="w-4 h-4" /> No</span>
                    }
                </div>
                <div className="p-4 flex items-center justify-between">
                    <span className="text-gray-300">Model Available</span>
                    {isLoading ? <span className="text-gray-500">Checking...</span> :
                        status.models.length > 0 ? <span className="text-green-400 flex items-center gap-1"><Check className="w-4 h-4" /> {status.models[0]}</span> :
                            <span className="text-yellow-400 flex items-center gap-1"><AlertCircle className="w-4 h-4" /> None found</span>
                    }
                </div>
            </div>

            <div className="flex justify-between pt-8">
                <button onClick={onBack} className="text-gray-400 hover:text-white transition-colors">Back</button>
                <button
                    onClick={onNext}
                    disabled={!status.running}
                    className="btn-primary"
                >
                    Finish Setup
                </button>
            </div>
        </motion.div>
    )
}

function FinalStep({ config, onComplete }) {
    const [isSaving, setIsSaving] = useState(false)

    useEffect(() => {
        const save = async () => {
            setIsSaving(true)
            try {
                await fetch('/api/config/save', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(config)
                })
                // Allow a moment for the user to see success
                setTimeout(() => {
                    onComplete()
                }, 2000)
            } catch (e) {
                console.error(e)
            }
            setIsSaving(false)
        }
        save()
    }, [])

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="text-center py-20 px-6"
        >
            <div className="w-20 h-20 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-8 animate-bounce">
                <Check className="w-10 h-10 text-green-400" />
            </div>

            <h1 className="text-4xl font-bold mb-4">All Set!</h1>
            <p className="text-xl text-gray-400 max-w-lg mx-auto mb-10">
                Sugar is ready. Redirecting to dashboard...
            </p>
        </motion.div>
    )
}

function SetupWizard({ config, updateConfig, onComplete }) {
    const [step, setStep] = useState(0)

    const next = () => setStep(s => s + 1)
    const back = () => setStep(s => s - 1)

    return (
        <div className="min-h-screen bg-gray-950 flex flex-col items-center justify-center p-4">
            <div className="w-full max-w-2xl">
                <AnimatePresence mode="wait">
                    {step === 0 && <WelcomeStep key="welcome" onNext={next} />}
                    {step === 1 && <VaultStep key="vault" config={config} updateConfig={updateConfig} onNext={next} onBack={back} />}
                    {step === 2 && <LinearStep key="linear" config={config} updateConfig={updateConfig} onNext={next} onBack={back} />}
                    {step === 3 && <OllamaStep key="ollama" config={config} updateConfig={updateConfig} onNext={next} onBack={back} />}
                    {step === 4 && <FinalStep key="final" config={config} onComplete={onComplete} />}
                </AnimatePresence>

                {step > 0 && step < 4 && (
                    <div className="flex justify-center gap-2 mt-12">
                        {[1, 2, 3].map((i) => (
                            <div
                                key={i}
                                className={clsx(
                                    "w-2 h-2 rounded-full transition-colors",
                                    step >= i ? "bg-sugar-500" : "bg-gray-800"
                                )}
                            />
                        ))}
                    </div>
                )}
            </div>
        </div>
    )
}

// --- Main App ---

export default function App() {
    const [loading, setLoading] = useState(true)
    const [config, setConfig] = useState({
        obsidian_vault_path: '',
        linear_api_key: '',
        ollama_model: 'mistral',
        ollama_host: 'http://localhost:11434',
        telegram_bot_token: ''
    })
    const [isConfigured, setIsConfigured] = useState(false)

    useEffect(() => {
        fetch('/api/status').then(r => r.json()).then(data => {
            if (data.current_config) {
                setConfig(prev => ({ ...prev, ...data.current_config }))
            }
            // Use obsidian_vault_valid as proxy for "is configured"
            // Start dashboard if configured
            if (data.obsidian_vault_valid) {
                setIsConfigured(true)
            }
            setLoading(false)
        })
    }, [])

    const updateConfig = (key, value) => {
        setConfig(prev => ({ ...prev, [key]: value }))
    }

    if (loading) return <div className="min-h-screen bg-gray-950 flex items-center justify-center text-sugar-500">Loading Sugar...</div>

    if (isConfigured) {
        return <Dashboard config={config} updateConfig={updateConfig} />
    }

    return <SetupWizard config={config} updateConfig={updateConfig} onComplete={() => setIsConfigured(true)} />
}
