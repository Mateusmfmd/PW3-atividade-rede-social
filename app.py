# Configurações do Flask, Banco de Dados e SocketIO
from flask import Flask
from flask_socketio import SocketIO
from models.database import db, atualizar_banco
from models.exemplos import carregar_exemplos
from controllers import routes, chat
import os

# Dados de exemplo (pessoas, fotos, curtidas, comentários e chat). Senha das contas: 123456
CARREGAR_EXEMPLOS = True

app = Flask(__name__, template_folder='views')

# Configurações de Banco (SQLite)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'models', 'rede_social.sqlite3')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Sessão e Uploads
app.config['SECRET_KEY'] = 'chave_secreta_rede_social'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

# Liga o banco ao app fora do __main__, assim as rotas sempre enxergam o db
db.init_app(app=app)

# Inicialização do SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

routes.init_app(app)
chat.init_app(socketio)

if __name__ == '__main__':
    # Cria as pastas de uploads (posts e fotos de perfil) caso não existam
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'perfil'), exist_ok=True)
    with app.app_context():
        atualizar_banco()  # db.create_all() + colunas novas em bancos antigos
        if CARREGAR_EXEMPLOS:
            carregar_exemplos(app.config['UPLOAD_FOLDER'])  # só cria na primeira vez
    # debug=True mantém o recarregamento automático ao salvar arquivos.
    # use_debugger=False: o depurador do navegador mostrava como "erro 500 / ConnectionError"
    # o fechamento normal do WebSocket ao sair da página do chat. Erros de verdade
    # continuam aparecendo no terminal.
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_debugger=False,
                 allow_unsafe_werkzeug=True)
