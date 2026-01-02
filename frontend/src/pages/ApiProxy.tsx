/**
 * ApiProxy Page
 * 
 * Test console for verifying API endpoints
 */
import { useState } from 'react';
import { Play, Loader2, CheckCircle2, AlertTriangle, Terminal, Copy, Check } from 'lucide-react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
// import { useAccountStore } from '../stores/useAccountStore'; // Unused import removed
import { useAuthStore } from '../stores/useAuthStore';

export default function ApiProxy() {
    // const { availableModels } = useAccountStore(); // Unused
    const { user } = useAuthStore();
    const [selectedProtocol, setSelectedProtocol] = useState<'openai' | 'claude' | 'gemini'>('openai');
    const [testModel, setTestModel] = useState('');
    const [testInput, setTestInput] = useState('Hello, tell me a joke.');
    const [response, setResponse] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [status, setStatus] = useState<'idle' | 'success' | 'error'>('idle');
    const [codeLang, setCodeLang] = useState<'curl' | 'python' | 'csharp'>('curl');
    const [copied, setCopied] = useState(false);

    // Use current page origin as API base (works in both dev and production)
    const apiBase = window.location.origin;
    const apiKey = user?.api_key || 'sk-antigravity';

    // User's preferred models for quick selection
    const preferredModels = [
        'claude-opus-4-5-thinking',
        'claude-sonnet-4-5-thinking',
        'gemini-3-flash',
        'gemini-3-pro-high',
        'gemini-3-pro-low',
        'gpt-oss-120b-medium',
    ];

    const handleTest = async () => {
        setIsLoading(true);
        setResponse('');
        setStatus('idle');

        try {
            let url = '';
            let body = {};
            let headers: Record<string, string> = {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${apiKey}`
            };

            if (selectedProtocol === 'openai') {
                url = `${apiBase}/v1/chat/completions`;
                body = {
                    model: testModel || 'gemini-3-flash',
                    messages: [{ role: 'user', content: testInput }]
                };
            } else if (selectedProtocol === 'claude') {
                url = `${apiBase}/v1/messages`;
                headers['x-api-key'] = apiKey;
                headers['anthropic-version'] = '2023-06-01';
                body = {
                    model: testModel || 'claude-sonnet-4-5-thinking',
                    max_tokens: 1024,
                    messages: [{ role: 'user', content: testInput }]
                };
            } else {
                // Gemini Native Protocol
                const model = testModel || 'gemini-3-flash';
                // Pass API key in query param for Gemini SDK compatibility
                url = `${apiBase}/v1beta/models/${model}:generateContent?key=${apiKey}`;

                // For native Gemini through proxy, remove Bearer to simulate SDK behavior
                delete headers['Authorization'];

                body = {
                    contents: [{
                        parts: [{ text: testInput }]
                    }]
                };
            }

            const res = await fetch(url, {
                method: 'POST',
                headers,
                body: JSON.stringify(body)
            });

            const data = await res.json();

            if (!res.ok) {
                throw new Error(data.detail || data.error?.message || res.statusText);
            }

            setResponse(JSON.stringify(data, null, 2));
            setStatus('success');
        } catch (e: any) {
            setResponse(`Error: ${e.message}`);
            setStatus('error');
        } finally {
            setIsLoading(false);
        }
    };

    const generateCode = () => {
        const model = testModel || (selectedProtocol === 'openai' ? 'gemini-3-flash' : selectedProtocol === 'claude' ? 'claude-sonnet-4-5-thinking' : 'gemini-3-flash');
        // Simple escape for demo purposes
        const input = testInput.replace(/"/g, '\\"').replace(/\n/g, '\\n');

        if (codeLang === 'curl') {
            if (selectedProtocol === 'openai') {
                return `curl ${apiBase}/v1/chat/completions \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer ${apiKey}" \\
  -d '{
    "model": "${model}",
    "messages": [
      {
        "role": "user",
        "content": "${input}"
      }
    ]
  }'`;
            } else if (selectedProtocol === 'claude') {
                return `curl ${apiBase}/v1/messages \\
  -H "x-api-key: ${apiKey}" \\
  -H "anthropic-version: 2023-06-01" \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "${model}",
    "max_tokens": 1024,
    "messages": [
      {
        "role": "user",
        "content": "${input}"
      }
    ]
  }'`;
            } else {
                return `curl "${apiBase}/v1beta/models/${model}:generateContent?key=${apiKey}" \\
  -H "Content-Type: application/json" \\
  -d '{
    "contents": [{
      "parts": [{"text": "${input}"}]
    }]
  }'`;
            }
        } else if (codeLang === 'python') {
            if (selectedProtocol === 'openai') {
                return `from openai import OpenAI

client = OpenAI(
    base_url="${apiBase}/v1",
    api_key="${apiKey}"
)

response = client.chat.completions.create(
    model="${model}",
    messages=[
        {"role": "user", "content": "${input}"}
    ]
)

print(response.choices[0].message.content)`;
            } else if (selectedProtocol === 'claude') {
                return `import anthropic

client = anthropic.Anthropic(
    base_url="${apiBase}/v1",
    api_key="${apiKey}"
)

message = client.messages.create(
    model="${model}",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "${input}"}
    ]
)

print(message.content)`;
            } else {
                return `import requests
import json

url = "${apiBase}/v1beta/models/${model}:generateContent?key=${apiKey}"
headers = {'Content-Type': 'application/json'}
data = {
    "contents": [{
        "parts": [{"text": "${input}"}]
    }]
}

response = requests.post(url, headers=headers, json=data)
print(response.json())`;
            }
        } else {
            // C#
            if (selectedProtocol === 'openai') {
                return `using OpenAI;

var client = new OpenAIClient(
    new Uri("${apiBase}/v1"),
    new AzureKeyCredential("${apiKey}")
);

var response = await client.GetChatCompletionsAsync(
    new ChatCompletionsOptions()
    {
        DeploymentName = "${model}",
        Messages = { new ChatRequestUserMessage("${input}") }
    }
);

Console.WriteLine(response.Value.Choices[0].Message.Content);`;
            } else if (selectedProtocol === 'claude') {
                return `// Using HttpClient
using System.Net.Http;
using System.Text;
using System.Text.Json;

var client = new HttpClient();
var request = new HttpRequestMessage(HttpMethod.Post, "${apiBase}/v1/messages");
request.Headers.Add("x-api-key", "${apiKey}");
request.Headers.Add("anthropic-version", "2023-06-01");

var json = JsonSerializer.Serialize(new
{
    model = "${model}",
    max_tokens = 1024,
    messages = new[] { new { role = "user", content = "${input}" } }
});

request.Content = new StringContent(json, Encoding.UTF8, "application/json");
var response = await client.SendAsync(request);
var responseString = await response.Content.ReadAsStringAsync();
Console.WriteLine(responseString);`;
            } else {
                return `// Using HttpClient
using System.Net.Http;
using System.Text;

var client = new HttpClient();
var url = "${apiBase}/v1beta/models/${model}:generateContent?key=${apiKey}";

var json = "{\\"contents\\": [{\\"parts\\": [{\\"text\\": \\"${input}\\"}]}]}";
var content = new StringContent(json, Encoding.UTF8, "application/json");

var response = await client.PostAsync(url, content);
var responseString = await response.Content.ReadAsStringAsync();
Console.WriteLine(responseString);`;
            }
        }
    };

    const handleCopyCode = () => {
        navigator.clipboard.writeText(generateCode());
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <div className="p-6 max-w-[95%] mx-auto h-[calc(100vh-4rem)] flex flex-col">
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900 dark:text-white">API Proxy</h1>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                        Test and verify your API endpoints
                    </p>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1 min-h-0">
                {/* Request Panel */}
                <div className="lg:col-span-1 bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-6 flex flex-col overflow-hidden">
                    <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                        <Terminal className="w-5 h-5 text-indigo-500" />
                        Request
                    </h2>

                    <div className="space-y-4 flex-1 overflow-y-auto pr-2">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Protocol</label>
                            <div className="grid grid-cols-3 gap-2 bg-gray-100 dark:bg-gray-700 p-1 rounded-lg">
                                {(['openai', 'claude', 'gemini'] as const).map(p => (
                                    <button
                                        key={p}
                                        onClick={() => setSelectedProtocol(p)}
                                        className={`px-3 py-1.5 rounded-md text-sm font-medium capitalize transition-all ${selectedProtocol === p
                                            ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm'
                                            : 'text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                                            }`}
                                    >
                                        {p}
                                    </button>
                                ))}
                            </div>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Model</label>
                            <input
                                type="text"
                                value={testModel}
                                onChange={(e) => setTestModel(e.target.value)}
                                placeholder={selectedProtocol === 'openai' ? 'gpt-4' : selectedProtocol === 'claude' ? 'claude-3-opus-20240229' : 'gemini-1.5-pro'}
                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-indigo-500"
                            />
                            <div className="mt-2 flex flex-wrap gap-2">
                                {preferredModels.map(m => (
                                    <button
                                        key={m}
                                        onClick={() => setTestModel(m)}
                                        className="text-xs px-2 py-1 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded text-gray-600 dark:text-gray-300 transition-colors"
                                    >
                                        {m}
                                    </button>
                                ))}
                            </div>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Input</label>
                            <textarea
                                value={testInput}
                                onChange={(e) => setTestInput(e.target.value)}
                                rows={5}
                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm font-mono resize-none focus:ring-2 focus:ring-indigo-500"
                            />
                        </div>
                    </div>

                    <div className="mt-6 pt-4 border-t border-gray-100 dark:border-gray-700">
                        <button
                            onClick={handleTest}
                            disabled={isLoading}
                            className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg flex items-center justify-center gap-2 font-medium transition-colors disabled:opacity-50"
                        >
                            {isLoading ? (
                                <>
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                    Testing...
                                </>
                            ) : (
                                <>
                                    <Play className="w-4 h-4 fill-current" />
                                    Send Request
                                </>
                            )}
                        </button>
                    </div>
                </div>

                {/* Right Column: Code Snippet + Response */}
                <div className="lg:col-span-2 flex flex-col gap-6 min-h-0">
                    {/* Code Snippet Panel */}
                    <div className="bg-gray-900 rounded-xl shadow-sm border border-gray-800 p-0 flex flex-col overflow-hidden relative" style={{ maxHeight: '40%' }}>
                        <div className="flex items-center justify-between px-4 py-3 bg-gray-800 border-b border-gray-700 shrink-0">
                            <div className="flex items-center gap-3">
                                <span className="text-sm font-medium text-gray-300">Code Implementation</span>
                                <select
                                    value={codeLang}
                                    onChange={(e) => setCodeLang(e.target.value as any)}
                                    className="bg-gray-700 border-none text-xs text-white rounded px-2 py-1 focus:ring-1 focus:ring-indigo-500"
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
                        <div className="flex-1 overflow-auto bg-[#1e1e1e]">
                            <SyntaxHighlighter
                                language={codeLang === 'curl' ? 'bash' : codeLang}
                                style={vscDarkPlus}
                                customStyle={{ margin: 0, height: '100%', fontSize: '12px' }}
                                showLineNumbers={true}
                                wrapLines={true}
                                wrapLongLines={true}
                            >
                                {generateCode()}
                            </SyntaxHighlighter>
                        </div>
                    </div>

                    {/* Response Panel */}
                    <div className="flex-1 bg-gray-900 rounded-xl shadow-sm border border-gray-800 p-0 flex flex-col overflow-hidden relative">
                        <div className="flex items-center justify-between px-4 py-3 bg-gray-800 border-b border-gray-700 shrink-0">
                            <span className="text-sm font-medium text-gray-300">Response</span>
                            {status === 'success' && <span className="flex items-center gap-1 text-xs text-green-400"><CheckCircle2 className="w-3 h-3" /> 200 OK</span>}
                            {status === 'error' && <span className="flex items-center gap-1 text-xs text-red-400"><AlertTriangle className="w-3 h-3" /> Error</span>}
                        </div>
                        <div className="flex-1 overflow-auto bg-[#1e1e1e]">
                            {response ? (
                                <SyntaxHighlighter
                                    language="json"
                                    style={vscDarkPlus}
                                    customStyle={{ margin: 0, height: '100%', fontSize: '12px' }}
                                    wrapLines={true}
                                    wrapLongLines={true}
                                >
                                    {response}
                                </SyntaxHighlighter>
                            ) : (
                                <div className="p-4 text-gray-600 font-mono text-xs">// Response will appear here...</div>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
