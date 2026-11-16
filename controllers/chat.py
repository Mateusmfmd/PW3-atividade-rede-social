# Handlers e eventos do SocketIO (connect, join, msg)
from flask import session, request, url_for
from flask_socketio import emit
from models.database import db, Usuario, Mensagem

# Quem está com o chat aberto agora: {sid: id do usuário}
conectados = {}


def perfil_publico(usuario):
    """Dados que o navegador recebe sobre um usuário (sempre lidos do banco/sessão)."""
    return {
        'id': usuario.id,
        'nome': usuario.nome,
        'foto': url_for('static', filename='uploads/perfil/' + usuario.foto) if usuario.foto else None,
    }


def lista_online():
    ids = sorted(set(conectados.values()))
    usuarios = Usuario.query.filter(Usuario.id.in_(ids)).all() if ids else []
    return [perfil_publico(u) for u in usuarios]


def init_app(socketio):

    @socketio.on('connect')
    def conectar():
        # Recusa a conexão de quem não está logado
        if 'user_id' not in session:
            return False

    @socketio.on('join')
    def entrar(data=None):
        ja_estava = session['user_id'] in conectados.values()
        conectados[request.sid] = session['user_id']
        if not ja_estava:
            emit('status', {'msg': f"{session['usuario_nome']} entrou no chat"}, broadcast=True)
        emit('online', lista_online(), broadcast=True)

    @socketio.on('msg')
    def mensagem(data):
        texto = str((data or {}).get('msg', '')).strip()[:500]
        if not texto:
            return

        usuario = db.session.get(Usuario, session['user_id'])
        if usuario is None:
            return

        # Guarda no histórico
        nova = Mensagem(texto, usuario.id)
        db.session.add(nova)
        db.session.commit()

        data = {
            'autor': perfil_publico(usuario),   # nome vem do banco/sessão, não do navegador
            'usuario': session['usuario_nome'],
            'msg': texto,
            'hora': nova.data.strftime('%H:%M'),
        }
        emit('showmsg', data, broadcast=True)

    @socketio.on('digitando')
    def digitando(data=None):
        # Avisa os outros (menos quem está digitando)
        emit('digitando', {'nome': session['usuario_nome']}, broadcast=True, include_self=False)

    @socketio.on('disconnect')
    def sair(*args):
        uid = conectados.pop(request.sid, None)
        if uid is not None and uid not in conectados.values():
            emit('status', {'msg': f"{session.get('usuario_nome', 'Alguém')} saiu do chat"}, broadcast=True)
        emit('online', lista_online(), broadcast=True)
