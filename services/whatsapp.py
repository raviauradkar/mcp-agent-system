"""
WhatsApp Bot Service - Flask application for handling WhatsApp messages via Twilio.

This service integrates with the MCP agent to provide AI-powered WhatsApp bot functionality.
"""

from flask import Flask, request
from twilio.rest import Client
import signal
import sys
import os
from pathlib import Path
import pyttsx3
import requests
import asyncio
import time

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_config
from mcp_agent import MCPAgent

# Initialize configuration
config = get_config()

# Validate required Twilio credentials
if not config.TWILIO_ACCOUNT_SID or not config.TWILIO_AUTH_TOKEN:
    print("ERROR: TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set in environment variables")
    sys.exit(1)

# Initialize Twilio client
client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)

# Globals
log_file = "twilio.log"
log_fh = sys.stdout
msg_num = 0
status_num = 0
ob_num = 0
mcp_agent = None

app = Flask(__name__)
app.debug = True


def create_mcp_agent():
    """Create and initialize the MCP Agent"""
    agent = MCPAgent(config=None)
    if agent is None:
        log("Error creating MCP agent")
    else:
        log("Created MCP agent successfully")
    return agent


def generate(prompt, model="mistral:latest", max_tokens=50, temperature=0.7):
    """
    Call Ollama/Mistral and return generated text or full response.
    """
    SERVER_URL = config.OLLAMA_URL.replace("/api/chat", "/api/generate")

    jsonNew = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            "temperature": temperature,
            "top_p": 0.9,
            "top_k": 40,
            "repeat_penalty": 1.1,
            "stop": ["\n\n"]
        }
    }
    log(f"ollama- <{jsonNew}>")

    resp = requests.post(SERVER_URL, json=jsonNew)

    data = resp.json()
    log(f"response- <{data}>")

    if "response" in data:
        return data["response"]
    elif "completions" in data:
        return data["completions"][0]["data"]["text"]
    else:
        return data  # raw fallback


def doTTS(msg, tofile):
    """Generate text-to-speech audio file"""
    log(f"doTTS <{msg}> to <{tofile}>")
    speaker = pyttsx3.init()
    speaker.setProperty('rate', 150)
    speaker.setProperty('volume', 1.0)
    try:
        speaker.say(msg)
        speaker.save_to_file(msg, tofile)
    except:
        print("Error in TTS")


def log(*args):
    """Log messages to console or file"""
    msg = ""
    for arg in args:
        msg += str(arg)
    print(msg, file=log_fh, flush=True)


def signal_handler(sig, frame):
    """Handle interrupt signals"""
    house_cleaning(sig)
    sys.exit(0)


def house_cleaning(sig: int):
    """Cleanup resources on shutdown"""
    log(f'Signal {sig} received, cleaning up')
    if log_fh is not sys.stdout:
        log_fh.close()
        print("Closed log file")


def incMsg():
    global msg_num
    msg_num += 1
    return msg_num


def incStatus():
    global status_num
    status_num += 1
    return status_num


def incObd():
    global ob_num
    ob_num += 1
    return ob_num


def loghdr(msg, num, start):
    """Log a header/separator line"""
    delimit = "_ " if start else "- "
    log(delimit * 30, msg, "#", num, " ", delimit * 30)


@app.route("/")
def hello():
    """Default route"""
    log("default route")
    return {
        "Result": "Hello drivers, this app will help you fix your car issues"
    }


def send_tts_message(msg, recp):
    """Send a message with TTS media"""
    log(f"\tsend_tts_message <{recp}> to <{msg}>")
    resp = client.messages.create(
        media_url=['https://channels.kirusa.com/webplay/b2ff37a28db425f6efb65e4e67363539/'],
        from_=config.TWILIO_WHATSAPP_NUMBER,
        to=recp
    )
    log(resp)


def send_message(msg, recp):
    """Send a WhatsApp message, splitting if too long"""
    log(f"\tsend_message to <{recp}>")

    if not msg or not recp:
        log("\tERROR: Missing message or recipient!")
        return None

    MAX_LENGTH = 1500

    # Split message into chunks
    if len(msg) > MAX_LENGTH:
        chunks = [msg[i:i + MAX_LENGTH] for i in range(0, len(msg), MAX_LENGTH)]
    else:
        chunks = [msg]

    log(f"\tSending {len(chunks)} message(s)...")
    responses = []

    for i, chunk in enumerate(chunks):
        try:
            # Add part number if multiple chunks
            body = f"({i + 1}/{len(chunks)})\n{chunk}" if len(chunks) > 1 else chunk

            resp = client.messages.create(
                body=body,
                from_=config.TWILIO_WHATSAPP_NUMBER,
                to=recp
            )
            log(f"\t✅ Part {i + 1} sent! SID: {resp.sid}")
            responses.append(resp)

            # Delay between messages
            if i < len(chunks) - 1:
                time.sleep(1)

        except Exception as e:
            log(f"\t❌ ERROR: {e}")
            raise

    return responses[0] if len(responses) == 1 else responses


def process_message(msg: str, name: str):
    """Process incoming message and generate response"""
    if msg.casefold() == "hi":
        message = f"{name}, welcome to the car help bot. Send your car issue and I will try to help you"
    elif "echo:" in msg.casefold():
        parts = msg.casefold().split(":")
        message = parts[1].upper()
    else:
        log(f"For user {name} will get answer for <{msg}> from LLM")
        if mcp_agent is None:
            log("Error: MCP agent not initialized")
            message = generate(msg, 501)
        else:
            message = asyncio.run(mcp_agent.run(name, msg))

    return message


def talk2oper(name: str, msg: str):
    """Interactive operator chat (if enabled)"""
    m = ""
    if os.path.isfile('ispresent'):
        print("✅ - talking is allowed")
        m = input(f"Hello {name}, you asked <{msg}> :")
    else:
        m = f"Hello {name}, you asked <{msg}>- I am not here to answer, sorry\nYou can get automated responses by typing your question."
        print("❌ talking is not allowed, sorry")
    return m


def isTwilio(form):
    """Check if request is from Twilio"""
    deflv = "whywoudltthisbe"
    ispresent = form.get("ProfileName", deflv)
    return ispresent != deflv


@app.route("/webroot", methods=["POST"])
def webroot():
    """Main webhook endpoint for incoming WhatsApp messages"""
    num = incMsg()
    loghdr("webroot", num, True)

    form = request.form
    loghttp(request)
    sender = form["From"]
    msg = form["Body"]
    name = sender
    message = process_message(msg, name)

    loghdr("webroot", num, False)

    if message == "media":
        send_tts_message(msg, sender)
        return "OK", 200

    if isTwilio(form):  # twilio
        log(f"sending msg <{message}> to <{sender}>")
        send_message(message, sender)
        return "OK", 200
    else:
        return {
            "Result": message
        }


@app.route("/status", methods=["POST", "GET"])
def status():
    """Status webhook endpoint"""
    num = incStatus()
    loghdr("status", num, True)
    loghttp(request)
    loghdr("status", num, False)
    return "OK", 200


@app.route("/sendmessage", methods=["POST", "GET"])
def sendmessage():
    """Send outbound message"""
    num = incObd()
    msg = ""
    loghdr("outbound", num, True)
    try:
        form = request.form
        log(form)
        msg = form
    except:
        msg = "error"
        log(msg)
        return {"Result": msg}
    loghdr("outbound", num, False)

    recp = form["sendto"]
    message = form["message"]
    for num in recp.split(","):
        msg = send_message(message, f"WhatsApp:+{num.strip()}")
    return {
        "Result": msg
    }


@app.route("/sendinvite", methods=["POST", "GET"])
def sendinvite():
    """Send bot invitation"""
    message = f"whatsapp://send?phone={config.TWILIO_WHATSAPP_NUMBER}&text={config.TWILIO_SANDBOX_CODE}"
    num = incObd()

    loghdr("invite", num, True)
    try:
        form = request.form
        log(form)
    except:
        log("error, could not get data from body")
        return {"Result": "error"}

    loghdr("invite", num, False)
    recp = form["sendto"]
    for num in recp.split(","):
        msg = send_message(message, f"WhatsApp:+{num.strip()}")
    return {
        "Result": msg
    }


def has_no_empty_params(rule):
    """Check if route has no empty parameters"""
    defaults = rule.defaults if rule.defaults is not None else ()
    arguments = rule.arguments if rule.arguments is not None else ()
    return len(defaults) >= len(arguments)


@app.route("/site-map")
def site_map():
    """List all available routes"""
    from flask import url_for
    links = []
    for rule in app.url_map.iter_rules():
        if "GET" in rule.methods and has_no_empty_params(rule):
            url = url_for(rule.endpoint, **(rule.defaults or {}))
            links.append((url, rule.endpoint))
    return links


@app.route("/gs", methods=["POST", "GET"])
def gs():
    """Test endpoint"""
    num = incMsg()
    loghdr("gs", num, True)
    loghttp(request)
    loghdr("gs", num, False)
    return "786", 200


def loghttp(req):
    """Log HTTP request details"""
    form = req.form
    args = req.args
    log("type-", req.method)
    log("args-", args)
    log("forms-", form)
    log("get_data--> {0}".format(req.get_data()))


def main():
    """Entry point for WhatsApp bot service"""
    global log_fh, mcp_agent

    args = len(sys.argv)
    server_port = config.WHATSAPP_BOT_PORT

    # Check for log file argument
    log_file_path = None
    if args > 1:
        log_file_path = sys.argv[1]

    if log_file_path and log_file_path != "none":
        log_fh = open(log_file_path, 'w')

    print(f"Starting WhatsApp bot on port {server_port}")
    print("Adding signal handler ... ")
    signal.signal(signal.SIGINT, signal_handler)

    # Create MCP agent
    mcp_agent = create_mcp_agent()

    app.run(host='localhost', port=server_port, debug=True, use_reloader=False)


if __name__ == "__main__":
    main()
