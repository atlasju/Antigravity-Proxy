import React, { useState } from 'react';
import { api } from '../services/api';
import { Image as ImageIcon, Loader2, AlertTriangle, Download, Copy, Check, Terminal } from 'lucide-react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface GeneratedImage {
    url?: string;
    b64_json?: string;
    revised_prompt?: string;
}

export default function ImageGen() {
    const [prompt, setPrompt] = useState('');
    const [aspectRatio, setAspectRatio] = useState('1:1');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [images, setImages] = useState<GeneratedImage[]>([]);
    const [codeLang, setCodeLang] = useState<'curl' | 'python' | 'csharp'>('curl');
    const [copied, setCopied] = useState(false);

    const ratios = [
        { label: 'Square (1:1)', value: '1:1' },
        { label: 'Landscape (16:9)', value: '16:9' },
        { label: 'Portrait (9:16)', value: '9:16' },
        { label: 'Desktop (4:3)', value: '4:3' },
        { label: 'Mobile (3:4)', value: '3:4' },
    ];

    // Use current page origin as API base
    const apiBase = window.location.origin;

    const generateApiCode = () => {
        // Safe escape logic
        const safePrompt = (prompt || "A cute baby sea otter").replace(/"/g, '\\"').replace(/\n/g, '\\n');
        const size = aspectRatio === '1:1' ? '1024x1024' : aspectRatio === '16:9' ? '1920x1080' :
            aspectRatio === '9:16' ? '1080x1920' : aspectRatio === '4:3' ? '1024x768' : '768x1024';

        if (codeLang === 'curl') {
            return `curl ${apiBase}/v1/images/generations \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer sk-antigravity" \\
  -d '{
    "model": "gemini-3-pro-image",
    "prompt": "${safePrompt}",
    "n": 1,
    "size": "${size}"
  }'`;
        } else if (codeLang === 'python') {
            return `from openai import OpenAI

client = OpenAI(
    base_url="${apiBase}/v1",
    api_key="sk-antigravity"
)

response = client.images.generate(
    model="gemini-3-pro-image",
    prompt="${safePrompt}",
    size="${size}",
    n=1,
)

print(response.data[0].url)`;
        } else {
            return `using OpenAI;

var client = new OpenAIClient(
    new Uri("${apiBase}/v1"),
    new AzureKeyCredential("sk-antigravity")
);

var response = await client.GetImageGenerationsAsync(
    new ImageGenerationOptions()
    {
        DeploymentName = "gemini-3-pro-image",
        Prompt = "${safePrompt}",
        Size = ImageSize.Size1024x1024, // Note: Map string size manually if needed
    }
);

Console.WriteLine(response.Value.Data[0].Url);`;
        }
    };

    const handleCopyCode = () => {
        navigator.clipboard.writeText(generateApiCode());
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const handleGenerate = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!prompt.trim()) return;

        setLoading(true);
        setError(null);
        setImages([]);

        try {
            // Map ratio to resolution string as per OpenAI spec
            // Backend maps it back but we can send "1024x1024" or specific ratio suffixes if supported.
            // Our backend supports -16x9 suffix logic in parse_aspect_ratio, OR size string.
            // Let's send size string based on ratio for standard behavior, 
            // OR we can just send "1024x1024" and append suffix to model? 
            // Better: backend parses "16:9" if we pass that?
            // Checking backend: parse_aspect_ratio checks for "x".
            // If we send "1024x1024", it defaults to 1:1. 
            // If we send explicit resolution like "1920x1080" it might detect 16:9.

            let size = "1024x1024";
            if (aspectRatio === "16:9") size = "1920x1080";
            else if (aspectRatio === "9:16") size = "1080x1920";
            else if (aspectRatio === "4:3") size = "1024x768"; // Roughly
            else if (aspectRatio === "3:4") size = "768x1024";

            const res = await api.generateImage(prompt, size, 1);
            setImages(res.data);
        } catch (err: any) {
            setError(err.message || 'Failed to generate image');
        } finally {
            setLoading(false);
        }
    };

    const handleDownload = (img: GeneratedImage, index: number) => {
        let href = '';
        if (img.b64_json) {
            href = `data:image/png;base64,${img.b64_json}`;
        } else if (img.url) {
            href = img.url;
        }

        if (href) {
            const a = document.createElement('a');
            a.href = href;
            a.download = `antigravity-gen-${Date.now()}-${index + 1}.png`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        }
    };

    return (
        <div className="flex-1 bg-gray-50 dark:bg-gray-900 h-screen overflow-auto">
            <div className="max-w-[95%] mx-auto px-4 py-8">
                <div className="flex items-center gap-3 mb-8">
                    <div className="p-2 bg-indigo-100 dark:bg-indigo-900/30 rounded-lg">
                        <ImageIcon className="w-6 h-6 text-indigo-600 dark:text-indigo-400" />
                    </div>
                    <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                        Imagen 3 Studio
                    </h1>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    {/* Left Panel: Controls */}
                    <div className="lg:col-span-1 space-y-6">
                        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                            <form onSubmit={handleGenerate} className="space-y-6">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                        Prompt
                                    </label>
                                    <textarea
                                        value={prompt}
                                        onChange={(e) => setPrompt(e.target.value)}
                                        placeholder="Describe the image you want to generate..."
                                        className="w-full h-32 px-3 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none transition-all resize-none text-sm"
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                        Aspect Ratio
                                    </label>
                                    <div className="grid grid-cols-2 gap-2">
                                        {ratios.map((r) => (
                                            <button
                                                key={r.value}
                                                type="button"
                                                onClick={() => setAspectRatio(r.value)}
                                                className={`px-3 py-2 text-sm rounded-lg border transition-all ${aspectRatio === r.value
                                                    ? 'bg-indigo-50 dark:bg-indigo-900/30 border-indigo-200 dark:border-indigo-800 text-indigo-700 dark:text-indigo-300'
                                                    : 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-750 text-gray-600 dark:text-gray-400'
                                                    }`}
                                            >
                                                {r.label}
                                            </button>
                                        ))}
                                    </div>
                                </div>

                                <button
                                    type="submit"
                                    disabled={loading || !prompt.trim()}
                                    className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    {loading ? (
                                        <>
                                            <Loader2 className="w-4 h-4 animate-spin" />
                                            Generating...
                                        </>
                                    ) : (
                                        <>
                                            <ImageIcon className="w-4 h-4" />
                                            Generate
                                        </>
                                    )}
                                </button>
                            </form>
                        </div>
                    </div>

                    {/* Right Panel: Results */}
                    <div className="lg:col-span-2">
                        {error && (
                            <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-start gap-3">
                                <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400 shrink-0 mt-0.5" />
                                <div className="text-sm text-red-600 dark:text-red-400">
                                    <p className="font-medium">Generation Failed</p>
                                    <p className="mt-1 opacity-90">{error}</p>
                                </div>
                            </div>
                        )}

                        {images.length > 0 ? (
                            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                                <div className="grid grid-cols-1 gap-6">
                                    {images.map((img, idx) => (
                                        <div key={idx} className="relative group rounded-lg overflow-hidden bg-gray-100 dark:bg-gray-900">
                                            {img.b64_json ? (
                                                <img
                                                    src={`data:image/png;base64,${img.b64_json}`}
                                                    alt={`Generated image ${idx + 1}`}
                                                    className="w-full h-auto object-contain max-h-[600px] mx-auto"
                                                />
                                            ) : img.url ? (
                                                <img
                                                    src={img.url}
                                                    alt={`Generated image ${idx + 1}`}
                                                    className="w-full h-auto object-contain max-h-[600px] mx-auto"
                                                />
                                            ) : (
                                                <div className="aspect-square flex items-center justify-center text-gray-400">
                                                    No image data
                                                </div>
                                            )}

                                            <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-4">
                                                <button
                                                    onClick={() => handleDownload(img, idx)}
                                                    className="p-3 bg-white/20 hover:bg-white/30 text-white rounded-full backdrop-blur-sm transition-colors border border-white/20"
                                                    title="Download Image"
                                                >
                                                    <Download className="w-6 h-6" />
                                                </button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        ) : (
                            <div className="h-full min-h-[400px] flex flex-col items-center justify-center text-gray-400 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 border-dashed">
                                <div className="w-16 h-16 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mb-4">
                                    <ImageIcon className="w-8 h-8 opacity-50" />
                                </div>
                                <p className="text-lg font-medium text-gray-500">Ready to Create</p>
                                <p className="text-sm mt-2">Enter a prompt and click Generate to start</p>
                            </div>
                        )}

                        {/* API Code Snippet Panel */}
                        <div className="mt-8 bg-gray-900 rounded-xl shadow-sm border border-gray-800 p-0 flex flex-col overflow-hidden">
                            <div className="flex items-center justify-between px-4 py-3 bg-gray-800 border-b border-gray-700 shrink-0">
                                <div className="flex items-center gap-3">
                                    <Terminal className="w-4 h-4 text-indigo-400" />
                                    <span className="text-sm font-medium text-gray-300">API Usage</span>
                                    <select
                                        value={codeLang}
                                        onChange={(e) => setCodeLang(e.target.value as any)}
                                        className="bg-gray-700 border-none text-xs text-white rounded px-2 py-1 focus:ring-1 focus:ring-indigo-500 outline-none"
                                    >
                                        <option value="curl">cURL</option>
                                        <option value="python">Python</option>
                                        <option value="csharp">C#</option>
                                    </select>
                                </div>
                                <button
                                    onClick={handleCopyCode}
                                    className={`p-1.5 rounded transition-all flex items-center gap-1 text-xs font-medium px-2 ${copied
                                        ? 'bg-green-500/10 text-green-400 hover:bg-green-500/20'
                                        : 'hover:bg-gray-700 text-gray-400 hover:text-white'
                                        }`}
                                    title="Copy Code"
                                >
                                    {copied ? (
                                        <>
                                            <Check className="w-3.5 h-3.5" />
                                            <span>Copied!</span>
                                        </>
                                    ) : (
                                        <>
                                            <Copy className="w-3.5 h-3.5" />
                                            <span>Copy</span>
                                        </>
                                    )}
                                </button>
                            </div>
                            <div className="p-4 bg-[#1e1e1e] overflow-x-auto">
                                <SyntaxHighlighter
                                    language={codeLang === 'curl' ? 'bash' : codeLang}
                                    style={vscDarkPlus}
                                    customStyle={{ margin: 0, padding: 0, fontSize: '12px', background: 'transparent' }}
                                    wrapLines={true}
                                    wrapLongLines={true}
                                >
                                    {generateApiCode()}
                                </SyntaxHighlighter>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
