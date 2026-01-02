#!/usr/bin/env python3
"""
OAuth Relay for Antigravity Proxy

A standalone relay application that receives Google OAuth callbacks
and forwards them to your production server.

This allows you to add Google accounts to your production deployment
even when the OAuth client's redirect_uri is configured for localhost only.

USAGE:
    python oauth_relay.py --target https://your-production-server.com:56443

REQUIREMENTS:
    - Python 3.8+ (uses only standard library)

HOW IT WORKS:
    1. Run this script on your local machine
    2. Visit your production server and click "Login with Google (Relay)"
    3. Google redirects to localhost:8000 (this script)
    4. This script forwards the auth code to your production server
    5. Production server exchanges code for tokens and saves the account

Author: Antigravity Proxy
License: MIT
"""

import argparse
import json
import ssl
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from urllib.request import Request, urlopen
from urllib.error import URLError

# Default configuration
DEFAULT_PORT = 8000

# HTML Templates
SUCCESS_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>OAuth Success</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0;
        }}
        .card {{
            background: white;
            border-radius: 16px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 500px;
            text-align: center;
        }}
        .success-icon {{
            font-size: 64px;
            margin-bottom: 20px;
        }}
        h1 {{
            color: #22c55e;
            margin: 0 0 10px 0;
        }}
        .email {{
            background: #f3f4f6;
            padding: 10px 20px;
            border-radius: 8px;
            font-family: monospace;
            margin: 20px 0;
        }}
        .message {{
            color: #6b7280;
            line-height: 1.6;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="success-icon">✅</div>
        <h1>Account Added!</h1>
        <div class="email">{email}</div>
        <p class="message">{message}</p>
        <p class="message">You can now close this window and return to your production server.</p>
    </div>
</body>
</html>
"""

ERROR_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>OAuth Error</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #f87171 0%, #dc2626 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0;
        }}
        .card {{
            background: white;
            border-radius: 16px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 500px;
            text-align: center;
        }}
        .error-icon {{
            font-size: 64px;
            margin-bottom: 20px;
        }}
        h1 {{
            color: #dc2626;
            margin: 0 0 10px 0;
        }}
        .error-detail {{
            background: #fef2f2;
            padding: 15px;
            border-radius: 8px;
            color: #991b1b;
            font-family: monospace;
            text-align: left;
            white-space: pre-wrap;
            word-break: break-word;
            margin: 20px 0;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="error-icon">❌</div>
        <h1>OAuth Failed</h1>
        <div class="error-detail">{error}</div>
    </div>
</body>
</html>
"""

WAITING_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>OAuth Relay Running</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0;
        }}
        .card {{
            background: white;
            border-radius: 16px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 500px;
            text-align: center;
        }}
        h1 {{
            color: #1d4ed8;
            margin: 0 0 20px 0;
        }}
        .target {{
            background: #eff6ff;
            padding: 10px 20px;
            border-radius: 8px;
            font-family: monospace;
            margin: 20px 0;
            color: #1e40af;
        }}
        .instructions {{
            text-align: left;
            color: #4b5563;
            line-height: 1.8;
        }}
        .instructions li {{
            margin: 10px 0;
        }}
        code {{
            background: #f3f4f6;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="card">
        <h1>🔗 OAuth Relay Running</h1>
        <div class="target">Target: {target}</div>
        <div class="instructions">
            <ol>
                <li>Go to your production server</li>
                <li>Click <strong>"Login with Google (Relay)"</strong></li>
                <li>Complete Google authorization</li>
                <li>The callback will be handled automatically</li>
            </ol>
        </div>
    </div>
</body>
</html>
"""


class OAuthRelayHandler(BaseHTTPRequestHandler):
    """HTTP request handler for OAuth relay."""
    
    target_url = ""  # Will be set by main()
    
    def log_message(self, format, *args):
        """Custom log format with timestamps."""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {args[0]}")
    
    def do_GET(self):
        """Handle GET requests."""
        parsed = urlparse(self.path)
        
        if parsed.path == "/":
            # Show status page
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = WAITING_HTML.format(target=self.target_url)
            self.wfile.write(html.encode("utf-8"))
            
        elif parsed.path == "/api/oauth/callback":
            # Handle Google OAuth callback
            params = parse_qs(parsed.query)
            
            code = params.get("code", [None])[0]
            state = params.get("state", [None])[0]
            error = params.get("error", [None])[0]
            
            print("\n" + "=" * 60)
            print("  📥 Received OAuth callback from Google")
            print("=" * 60)
            
            if error:
                print(f"  ❌ Error: {error}")
                self.send_error_page(f"Google returned an error: {error}")
                return
            
            if not code or not state:
                print("  ❌ Error: Missing code or state parameter")
                self.send_error_page("Missing code or state parameter")
                return
            
            print(f"  ✓ Authorization code received: {code[:20]}...")
            print(f"  ✓ State token: {state[:20]}...")
            print(f"\n  🚀 Forwarding to production server...")
            print(f"     Target: {self.target_url}/api/oauth/relay-callback")
            
            # Forward to production server
            result = self.forward_to_production(code, state)
            
            if result.get("status") == "success":
                email = result.get("email", "Unknown")
                print(f"\n  ✅ SUCCESS!")
                print(f"     Account: {email}")
                print(f"     Message: {result.get('message', 'Account added successfully')}")
                print("=" * 60)
                print("\n  You can now close this relay or add more accounts.\n")
                self.send_success_page(email, result.get("message", "Account added successfully"))
            else:
                error_msg = result.get("detail", result.get("error", "Unknown error"))
                print(f"\n  ❌ FAILED!")
                print(f"     Error: {error_msg}")
                print("=" * 60 + "\n")
                self.send_error_page(error_msg)
        else:
            self.send_error(404)
    
    def forward_to_production(self, code: str, state: str) -> dict:
        """Forward the OAuth code to production server."""
        url = f"{self.target_url}/api/oauth/relay-callback"
        data = json.dumps({"code": code, "state": state}).encode("utf-8")
        
        # Create SSL context that doesn't verify certificates (for self-signed certs)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        try:
            req = Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urlopen(req, context=ctx, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except URLError as e:
            return {"error": f"Failed to connect to production server: {e}"}
        except json.JSONDecodeError:
            return {"error": "Invalid response from production server"}
        except Exception as e:
            return {"error": str(e)}
    
    def send_success_page(self, email: str, message: str):
        """Send success HTML page."""
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        html = SUCCESS_HTML.format(email=email, message=message)
        self.wfile.write(html.encode("utf-8"))
    
    def send_error_page(self, error: str):
        """Send error HTML page."""
        self.send_response(400)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        html = ERROR_HTML.format(error=error)
        self.wfile.write(html.encode("utf-8"))


def main():
    parser = argparse.ArgumentParser(
        description="OAuth Relay for Antigravity Proxy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python oauth_relay.py --target https://your-server.com:56443
    python oauth_relay.py -t https://your-server.com:56443 --open

The --target parameter is REQUIRED. It should be your Antigravity Proxy
production server URL where you want to add Google accounts.
        """
    )
    parser.add_argument(
        "--target", "-t",
        required=False,  # We handle this manually for better UX
        help="Your production server URL (e.g., https://your-server.com:56443)"
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=DEFAULT_PORT,
        help=f"Local port to listen on (default: {DEFAULT_PORT})"
    )
    parser.add_argument(
        "--open", "-o",
        action="store_true",
        help="Open browser to start OAuth flow automatically"
    )
    
    args = parser.parse_args()
    
    # Check if target is provided
    if not args.target:
        print("\n" + "=" * 60)
        print("  ⚠️  Missing required parameter: --target")
        print("=" * 60)
        print("\n  The --target parameter specifies your production server URL")
        print("  where you want to add Google accounts.")
        print("\n  Usage:")
        print("     python oauth_relay.py --target <YOUR_SERVER_URL>")
        print("\n  Examples:")
        print("     python oauth_relay.py --target https://example.com:56443")
        print("     python oauth_relay.py -t https://192.168.1.100:56443")
        print("\n  The URL should be your Antigravity Proxy production server")
        print("  (the same URL you use to access the web interface).\n")
        return
    
    # Set target URL for handler
    OAuthRelayHandler.target_url = args.target.rstrip("/")
    
    # Create server
    server = HTTPServer(("127.0.0.1", args.port), OAuthRelayHandler)
    
    print("\n" + "=" * 60)
    print("  🔗 Antigravity OAuth Relay")
    print("=" * 60)
    print(f"  📡 Listening on:  http://localhost:{args.port}")
    print(f"  🎯 Target server: {args.target}")
    print("=" * 60)
    print("\n  📋 Instructions:")
    print("     1. Go to your production server's Accounts page")
    print("     2. Click the green 'Relay Login' button")
    print("     3. Complete Google authorization in the browser")
    print("     4. Watch this terminal for progress updates")
    print("\n  ⏳ Waiting for OAuth callback...")
    print("     (Press Ctrl+C to stop)\n")
    
    if args.open:
        # Open browser to production server's relay OAuth start
        oauth_start_url = f"{args.target}/api/oauth/start-relay"
        print(f"  🌐 Opening browser to: {oauth_start_url}\n")
        webbrowser.open(oauth_start_url)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n  👋 Shutting down OAuth Relay...")
        print("     Goodbye!\n")
        server.shutdown()


if __name__ == "__main__":
    main()
