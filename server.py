import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse


def _json_bytes(payload):
    return json.dumps(payload, ensure_ascii=False).encode('utf-8')


def load_cadastros():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, 'r', encoding='utf-8') as handle:
        data = json.load(handle)
        return data.get('pessoas', []) if isinstance(data, dict) else []


def save_cadastros(entries):
    with open(DATA_FILE, 'w', encoding='utf-8') as handle:
        json.dump({'pessoas': entries}, handle, ensure_ascii=False, indent=2)
        handle.write('\n')


def load_quiz_data():
    if not os.path.exists(QUIZ_FILE):
        return {'doors': []}
    with open(QUIZ_FILE, 'r', encoding='utf-8') as handle:
        return json.load(handle)


def save_quiz_data(data):
    with open(QUIZ_FILE, 'w', encoding='utf-8') as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write('\n')

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(ROOT, 'cadastros.json')
QUIZ_FILE = os.path.join(ROOT, 'quiz-data.json')


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, payload, status=200):
        body = _json_bytes(payload)
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path):
        if not os.path.exists(path) or os.path.isdir(path):
            self.send_response(404)
            self.end_headers()
            return False

        content_type = 'text/html; charset=utf-8'
        if path.endswith('.css'):
            content_type = 'text/css; charset=utf-8'
        elif path.endswith('.js'):
            content_type = 'application/javascript; charset=utf-8'
        elif path.endswith('.json'):
            content_type = 'application/json; charset=utf-8'
        elif path.endswith('.png'):
            content_type = 'image/png'
        elif path.endswith('.jpg') or path.endswith('.jpeg'):
            content_type = 'image/jpeg'

        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.end_headers()
        with open(path, 'rb') as handle:
            self.wfile.write(handle.read())
        return True

    def do_HEAD(self):
        parsed = urlparse(self.path)

        if parsed.path in ("/", "", "/cadastrar", "/admin"):
            self.send_response(200)
        else:
            self.send_response(404)

        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        print('GET', parsed.path)
        if parsed.path in ('', '/'):
            self._send_file(os.path.join(ROOT, 'index.html'))
            return

        if parsed.path == '/cadastrar':
            self._send_file(os.path.join(ROOT, 'cadastro.html'))
            return

        if parsed.path == '/admin':
            self._send_file(os.path.join(ROOT, 'admin.html'))
            return

        if parsed.path == '/quiz-data.json':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            with open(QUIZ_FILE, 'r', encoding='utf-8') as handle:
                self.wfile.write(handle.read().encode('utf-8'))
            return

        if parsed.path == '/cadastros.json':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            with open(DATA_FILE, 'r', encoding='utf-8') as handle:
                self.wfile.write(handle.read().encode('utf-8'))
            return

        target = os.path.join(ROOT, parsed.path.lstrip('/'))
        if os.path.isdir(target):
            target = os.path.join(target, 'index.html')

        self._send_file(target)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == '/api/admin/save-quiz-data':
            length = int(self.headers.get('Content-Length', '0') or '0')
            body = self.rfile.read(length).decode('utf-8')
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                self._send_json({'error': 'JSON inválido'}, 400)
                return

            if not payload.get('doors'):
                self._send_json({'error': 'Formato inválido. Envie um JSON com o campo doors.'}, 400)
                return

            save_quiz_data(payload)
            self._send_json({'message': 'Perguntas salvas com sucesso'})
            return

        if parsed.path == '/api/admin/clear-cadastros':
            save_cadastros([])
            self._send_json({'message': 'Cadastros e ranking limpos com sucesso'})
            return

        if parsed.path != '/api/cadastrar':
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get('Content-Length', '0') or '0')
        body = self.rfile.read(length).decode('utf-8')

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self._send_json({'error': 'JSON inválido'}, 400)
            return

        name = (payload.get('name') or '').strip()
        birth_date = (payload.get('birthDate') or '').strip()
        if not name or not birth_date:
            self._send_json({'error': 'Nome e data de nascimento são obrigatórios'}, 400)
            return

        entries = load_cadastros()
        duplicate = any(entry.get('name', '').lower() == name.lower() and entry.get('birthDate') == birth_date for entry in entries)
        if duplicate:
            self._send_json({'error': 'Este cadastro já existe'}, 409)
            return

        entries.append({'name': name, 'birthDate': birth_date})
        save_cadastros(entries)

        self._send_json({'message': 'Cadastro realizado com sucesso'}, 201)

    def do_PUT(self):
        parsed = urlparse(self.path)
        if parsed.path != '/cadastros.json':
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get('Content-Length', '0'))
        body = self.rfile.read(length).decode('utf-8')

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            return

        save_cadastros(payload.get('pessoas', []))

        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(b'{"ok": true}')


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"Servidor iniciado na porta {port}")
    server.serve_forever()