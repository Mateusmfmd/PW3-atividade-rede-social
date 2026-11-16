# Rotas HTTP (login, cadastro, feed, upload, logout)
import os
import uuid
from datetime import datetime, timedelta
from flask import (render_template, request, redirect, url_for, flash, session,
                   current_app, jsonify, abort)
from werkzeug.security import generate_password_hash, check_password_hash
from models.database import db, Usuario, Post, Curtida, Comentario, Mensagem

EXTENSOES_PERMITIDAS = {'png', 'jpg', 'jpeg', 'gif'}

# Rotas que exigem login (o PDF pede /feed, /upload e /chat; as outras são dos extras)
ROTAS_PROTEGIDAS = ['/feed', '/upload', '/chat', '/excluir', '/curtir', '/comentar', '/perfil', '/explorar']


# ---------------- Funções auxiliares ----------------

def arquivo_permitido(nome_arquivo):
    """Confere se a extensão do arquivo está entre png, jpg, jpeg e gif."""
    return '.' in nome_arquivo and nome_arquivo.rsplit('.', 1)[1].lower() in EXTENSOES_PERMITIDAS


def salvar_imagem(arquivo, subpasta=''):
    """Renomeia com uuid4 (evita colisões e sobrescritas) e salva em UPLOAD_FOLDER."""
    extensao = arquivo.filename.rsplit('.', 1)[1].lower()
    nome_arquivo = f'{uuid.uuid4()}.{extensao}'
    pasta = os.path.join(current_app.config['UPLOAD_FOLDER'], subpasta)
    os.makedirs(pasta, exist_ok=True)
    arquivo.save(os.path.join(pasta, nome_arquivo))
    return nome_arquivo


def apagar_imagem(nome_arquivo, subpasta=''):
    """Remove a imagem do disco (os.remove), se ela existir."""
    caminho = os.path.join(current_app.config['UPLOAD_FOLDER'], subpasta, nome_arquivo)
    if os.path.exists(caminho):
        os.remove(caminho)


def tempo_relativo(data):
    """Transforma uma data em 'agora', 'há 5 min', 'há 2 h', 'ontem' ou '12/11/2026'."""
    segundos = (datetime.now() - data).total_seconds()
    if segundos < 60:
        return 'agora'
    if segundos < 3600:
        return f'há {int(segundos // 60)} min'
    if segundos < 86400:
        return f'há {int(segundos // 3600)} h'
    if segundos < 172800:
        return 'ontem'
    return data.strftime('%d/%m/%Y')


def foto_url(usuario):
    if usuario and usuario.foto:
        return url_for('static', filename='uploads/perfil/' + usuario.foto)
    return None


def pede_json():
    return request.headers.get('X-Requested-With') == 'fetch'


def init_app(app):

    app.jinja_env.filters['tempo'] = tempo_relativo
    app.jinja_env.globals['foto_url'] = foto_url

    # Disponibiliza o usuário logado em todos os templates como "eu"
    @app.context_processor
    def usuario_logado():
        eu = db.session.get(Usuario, session['user_id']) if 'user_id' in session else None
        return {'eu': eu}

    # ---------- Controle de acesso (middleware) ----------
    @app.before_request
    def verificar_autenticacao():
        rota_protegida = any(request.path.startswith(rota) for rota in ROTAS_PROTEGIDAS)
        if not rota_protegida:
            return

        if 'user_id' not in session:
            if pede_json():
                return jsonify({'erro': 'login necessário'}), 401
            flash('Entre na sua conta para ver essa página.', 'warning')
            return redirect(url_for('login'))

        # Sessão de um usuário que não existe mais no banco (ex.: banco apagado)
        if db.session.get(Usuario, session['user_id']) is None:
            session.clear()
            flash('Sua sessão expirou. Entre de novo.', 'warning')
            return redirect(url_for('login'))

    @app.route('/')
    def index():
        if 'user_id' in session:
            return redirect(url_for('feed'))
        return redirect(url_for('login'))

    # ---------- Cadastro ----------
    @app.route('/cadastro', methods=['GET', 'POST'])
    def cadastro():
        if request.method == 'POST':
            nome = request.form.get('nome', '').strip()
            email = request.form.get('email', '').strip().lower()
            senha = request.form.get('senha', '')

            if not nome or not email or not senha:
                flash('Preencha nome, e-mail e senha.', 'danger')
                return redirect(url_for('cadastro'))

            if len(senha) < 6:
                flash('A senha precisa ter pelo menos 6 caracteres.', 'danger')
                return redirect(url_for('cadastro'))

            # Não permite e-mail duplicado
            if Usuario.query.filter_by(email=email).first():
                flash('Esse e-mail já tem conta. Entre com ele ou use outro.', 'danger')
                return redirect(url_for('cadastro'))

            # Senha criptografada antes de gravar
            senha_hash = generate_password_hash(senha, method='scrypt')
            db.session.add(Usuario(nome, email, senha_hash))
            db.session.commit()

            flash('Conta criada. Agora é só entrar.', 'success')
            return redirect(url_for('login'))

        return render_template('cadastro.html')

    # ---------- Login ----------
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if 'user_id' in session and request.method == 'GET':
            return redirect(url_for('feed'))

        if request.method == 'POST':
            email = request.form.get('email', '').strip().lower()
            senha = request.form.get('senha', '')

            usuario = Usuario.query.filter_by(email=email).first()

            if usuario and check_password_hash(usuario.senha, senha):
                session.permanent = True
                session['user_id'] = usuario.id
                session['usuario_nome'] = usuario.nome
                session['usuario_email'] = usuario.email
                flash(f'Oi, {usuario.nome}!', 'success')
                return redirect(url_for('feed'))

            flash('E-mail ou senha não conferem.', 'danger')
            return redirect(url_for('login'))

        return render_template('login.html')

    # ---------- Logout ----------
    @app.route('/logout')
    def logout():
        session.clear()
        flash('Você saiu da conta.', 'info')
        return redirect(url_for('login'))

    # ---------- Feed ----------
    @app.route('/feed')
    def feed():
        # Do mais recente para o mais antigo
        posts = Post.query.order_by(Post.data_post.desc()).all()
        curtidos = {c.post_id for c in Curtida.query.filter_by(usuario_id=session['user_id'])}
        membros = Usuario.query.order_by(Usuario.criado_em.desc()).limit(8).all()
        total_usuarios = Usuario.query.count()

        # "Stories": quem publicou nas últimas 24 horas aparece primeiro, com anel colorido
        limite = datetime.now() - timedelta(hours=24)
        recentes = {p.usuario_id for p in posts if p.data_post >= limite}
        stories = sorted(Usuario.query.all(), key=lambda u: (u.id not in recentes, u.nome.lower()))

        return render_template('feed.html', posts=posts, curtidos=curtidos, membros=membros,
                               total_usuarios=total_usuarios, stories=stories, recentes=recentes)

    # ---------- Extra: explorar (todas as fotos em grade + busca de pessoas) ----------
    @app.route('/explorar')
    def explorar():
        posts = Post.query.order_by(Post.data_post.desc()).all()
        usuarios = Usuario.query.order_by(Usuario.nome).all()
        return render_template('explorar.html', posts=posts, usuarios=usuarios)

    # ---------- Upload ----------
    @app.route('/upload', methods=['POST'])
    def upload():
        arquivo = request.files.get('file')
        legenda = request.form.get('legenda', '').strip()[:255]

        if not arquivo or arquivo.filename == '':
            flash('Escolha uma foto para publicar.', 'danger')
            return redirect(url_for('feed'))

        if not arquivo_permitido(arquivo.filename):
            flash('Esse formato não vale. Use png, jpg, jpeg ou gif.', 'danger')
            return redirect(url_for('feed'))

        nome_arquivo = salvar_imagem(arquivo)
        db.session.add(Post(nome_arquivo, legenda, session['user_id']))
        db.session.commit()

        flash('Foto publicada.', 'success')
        return redirect(url_for('feed'))

    # ---------- Extra: excluir post ----------
    @app.route('/excluir/<int:id>', methods=['POST'])
    def excluir(id):
        post = db.session.get(Post, id)

        if post is None:
            flash('Essa publicação não existe mais.', 'danger')
        elif post.usuario_id != session['user_id']:
            flash('Só quem publicou pode excluir.', 'danger')
        else:
            apagar_imagem(post.imagem)   # remove do disco
            db.session.delete(post)      # remove do banco (curtidas e comentários vão junto)
            db.session.commit()
            flash('Publicação excluída.', 'info')

        return redirect(request.referrer or url_for('feed'))

    # ---------- Extra: curtir / descurtir (responde JSON para o JavaScript) ----------
    @app.route('/curtir/<int:id>', methods=['POST'])
    def curtir(id):
        post = db.session.get(Post, id)
        if post is None:
            abort(404)

        curtida = Curtida.query.filter_by(usuario_id=session['user_id'], post_id=id).first()
        if curtida:
            db.session.delete(curtida)
            curtido = False
        else:
            db.session.add(Curtida(session['user_id'], id))
            curtido = True
        db.session.commit()

        if pede_json():
            return jsonify({'curtido': curtido, 'total': len(post.curtidas)})
        return redirect(url_for('feed') + f'#post-{id}')

    # ---------- Extra: comentar ----------
    @app.route('/comentar/<int:id>', methods=['POST'])
    def comentar(id):
        texto = request.form.get('texto', '').strip()[:300]
        if db.session.get(Post, id) is None:
            abort(404)
        if texto:
            db.session.add(Comentario(texto, session['user_id'], id))
            db.session.commit()
        return redirect((request.referrer or url_for('feed')).split('#')[0] + f'#post-{id}')

    # ---------- Extra: página de perfil ----------
    @app.route('/perfil/<int:id>')
    def perfil(id):
        usuario = db.session.get(Usuario, id)
        if usuario is None:
            abort(404)
        posts = Post.query.filter_by(usuario_id=id).order_by(Post.data_post.desc()).all()
        total_curtidas = sum(len(p.curtidas) for p in posts)
        return render_template('perfil.html', usuario=usuario, posts=posts,
                               total_curtidas=total_curtidas)

    # ---------- Extra: editar perfil (foto e bio) ----------
    @app.route('/perfil/editar', methods=['GET', 'POST'])
    def editar_perfil():
        usuario = db.session.get(Usuario, session['user_id'])

        if request.method == 'POST':
            nome = request.form.get('nome', '').strip()[:100]
            usuario.bio = request.form.get('bio', '').strip()[:160] or None
            if nome:
                usuario.nome = nome
                session['usuario_nome'] = nome

            arquivo = request.files.get('foto')
            if arquivo and arquivo.filename:
                if not arquivo_permitido(arquivo.filename):
                    flash('Esse formato não vale. Use png, jpg, jpeg ou gif.', 'danger')
                    return redirect(url_for('editar_perfil'))
                if usuario.foto:
                    apagar_imagem(usuario.foto, 'perfil')
                usuario.foto = salvar_imagem(arquivo, 'perfil')

            if request.form.get('remover_foto') and usuario.foto:
                apagar_imagem(usuario.foto, 'perfil')
                usuario.foto = None

            db.session.commit()
            flash('Perfil salvo.', 'success')
            return redirect(url_for('perfil', id=usuario.id))

        return render_template('editar_perfil.html', usuario=usuario)

    # ---------- Chat ----------
    @app.route('/chat')
    def chat():
        # Últimas 50 mensagens, da mais antiga para a mais nova
        historico = Mensagem.query.order_by(Mensagem.data.desc()).limit(50).all()[::-1]
        return render_template('chat.html', historico=historico)

    @app.errorhandler(404)
    def nao_encontrado(e):
        return render_template('404.html'), 404
