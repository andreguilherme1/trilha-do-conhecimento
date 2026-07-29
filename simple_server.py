import http.server
import socketserver
import os
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / 'cadastros.json'
QUIZ_FILE = ROOT / 'quiz-data.json'

class Handler(http.server.SimpleHTTPRequestHandler):
    def _send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path, content_type='text/html; charset=utf-8'):
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.end_headers()
        with open(path, 'rb') as f:
            self.wfile.write(f.read())

    def do_GET(self):
        if self.path == '/cadastrar':
            self._send_file(ROOT / 'cadastro.html')
            return
        if self.path == '/admin':
            self._send_file(ROOT / 'admin.html')
            return
        if self.path == '/quiz-data.json':
            self._send_file(QUIZ_FILE, 'application/json; charset=utf-8')
            return
        if self.path == '/cadastros.json':
            self._send_file(DATA_FILE, 'application/json; charset=utf-8')
            return
        if self.path == '/':
            self._send_file(ROOT / 'index.html')
            return
        super().do_GET()

    def do_POST(self):
        if self.path == '/api/admin/save-quiz-data':
            length = int(self.headers.get('Content-Length', '0'))
            data = self.rfile.read(length).decode('utf-8')
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                self._send_json({'error': 'JSON inválido'}, 400)
                return
            if not payload.get('doors'):
                self._send_json({'error': 'Formato inválido. Envie um JSON com o campo doors.'}, 400)
                return
            with open(QUIZ_FILE, 'w', encoding='utf-8') as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
                f.write('\n')
            self._send_json({'message': 'Perguntas salvas com sucesso'})
            return

        if self.path == '/api/admin/clear-cadastros':
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump({'pessoas': []}, f, ensure_ascii=False, indent=2)
                f.write('\n')
            self._send_json({'message': 'Cadastros e ranking limpos com sucesso'})
            return

        if self.path == '/api/cadastrar':
            length = int(self.headers.get('Content-Length', '0'))
            data = self.rfile.read(length).decode('utf-8')
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                self._send_json({'error': 'JSON inválido'}, 400)
                return
            name = (payload.get('name') or '').strip()
            birth_date = (payload.get('birthDate') or '').strip()
            if not name or not birth_date:
                self._send_json({'error': 'Nome e data de nascimento são obrigatórios'}, 400)
                return
            if DATA_FILE.exists():
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    entries = json.load(f).get('pessoas', []) if json.load(f) else []
            else:
                entries = []
            duplicate = any(entry.get('name', '').lower() == name.lower() and entry.get('birthDate') == birth_date for entry in entries)
            if duplicate:
                self._send_json({'error': 'Este cadastro já existe'}, 409)
                return
            entries.append({'name': name, 'birthDate': birth_date})
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump({'pessoas': entries}, f, ensure_ascii=False, indent=2)
                f.write('\n')
            self._send_json({'message': 'Cadastro realizado com sucesso'}, 201)
            return

        self.send_response(404)
        self.end_headers()

with socketserver.TCPServer(('127.0.0.1', 8000), Handler) as httpd:
    print('Servidor ativo em http://127.0.0.1:8000')
    httpd.serve_forever()
