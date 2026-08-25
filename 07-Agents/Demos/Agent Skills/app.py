import os
import uuid
from flask import Flask, render_template, request, Response, stream_with_context, send_file, abort
from agno.db.in_memory import InMemoryDb
from agents import create_agent

app = Flask(__name__)
_memory = InMemoryDb()

ITINERARIES_DIR = os.path.join(os.path.dirname(__file__), "static", "itineraries")

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/streaming_chat", methods=["POST"])
def streaming_chat():
    user_input = request.form.get("input")

    if not user_input or not user_input.strip():
        return Response("Input cannot be empty", status=400)

    try:
        session_id = request.headers.get("X-Session-ID") or str(uuid.uuid4())
        agent = create_agent(session_id, _memory)
        streaming_output = agent.run(user_input, stream=True)

        def generate():
            try:
                for chunk in streaming_output:
                    if chunk.event == "RunContent":
                        yield chunk.content
                    elif chunk.event == "RunError":
                        yield f"\n\nError: {chunk.content}"
            except Exception as e:
                print(f"Streaming error: {e}")
                yield "\n\nI'm sorry, but something went wrong."

        response = Response(stream_with_context(generate()), mimetype="text/plain")
        response.headers["X-Session-ID"] = session_id
        response.headers["Cache-Control"] = "no-cache"
        response.headers["X-Accel-Buffering"] = "no"
        return response

    except Exception as e:
        print(f"Request error: {e}")
        response = Response(
            "\n\nI'm sorry, but something went wrong.",
            status=getattr(e, "status_code", 500),
            mimetype="text/plain; charset=utf-8",
        )
        response.headers["X-Session-ID"] = session_id
        return response

@app.route("/itineraries/<filename>", methods=["GET"])
def download_itinerary(filename):
    safe_name = os.path.basename(filename)
    if not safe_name.lower().endswith(".docx"):
        abort(404)

    path = os.path.join(ITINERARIES_DIR, safe_name)
    if not os.path.isfile(path):
        abort(404)

    return send_file(
        path,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        as_attachment=True,
        download_name=safe_name,
    )

@app.route("/itineraries/<filename>/preview", methods=["GET"])
def preview_itinerary(filename):
    safe_name = os.path.basename(filename)
    if not safe_name.lower().endswith(".docx"):
        abort(404)

    preview_name = os.path.splitext(safe_name)[0] + ".html"
    path = os.path.join(ITINERARIES_DIR, preview_name)
    if not os.path.isfile(path):
        abort(404)

    return send_file(path, mimetype="text/html")
