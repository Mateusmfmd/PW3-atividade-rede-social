# Dados de exemplo: o site já abre com pessoas, fotos, curtidas, comentários e mensagens.
# Roda sozinho uma única vez (ao iniciar o app.py). Para desligar, mude
# CARREGAR_EXEMPLOS para False no app.py.
#
# Todas as contas de exemplo usam a senha: 123456
# As imagens ficam em static/exemplos e são copiadas para static/uploads
# com nome gerado por uuid4, igual a um upload normal.
import hashlib
import os
import shutil
import uuid
from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash

from models.database import db, Usuario, Post, Curtida, Comentario, Mensagem

SENHA_EXEMPLO = '123456'

# (apelido, nome, e-mail, bio, foto de perfil, cadastrado há quantos dias)
USUARIOS = [
    ('carla', 'Carla Souza', 'carla@exemplo.com', 'Fotografia, café e pôr do sol. 📸', 'perfil-carla.jpg', 20),
    ('ana', 'Ana Lima', 'ana@exemplo.com', 'Clube de ciências e viagens sempre que dá. 🔬', 'perfil-ana.jpg', 18),
    ('bruno', 'Bruno Alves', 'bruno@exemplo.com', 'Basquete no intervalo. 🏀', None, 15),
    ('bia', 'Beatriz Rocha', 'bia@exemplo.com', 'Plantas, livros e playlists.', 'perfil-bia.jpg', 12),
    ('lucas', 'Lucas Martins', 'lucas@exemplo.com', 'Programo nas horas vagas. Flask é vida.', 'perfil-lucas.jpg', 10),
    ('joao', 'João Pedro', 'joao@exemplo.com', 'Sempre no chat. 💬', None, 6),
]

# (autor, arquivo em static/exemplos, legenda, publicado há quantas horas)
POSTS = [
    ('bruno', 'por-do-sol.jpg', 'fim de tarde na quadra', 2),
    ('carla', 'cafe.jpg', 'café antes da prova de matemática ☕', 5),
    ('ana', 'vulcao.jpg', 'feira de ciências: nosso vulcão funcionou!! 🌋', 20),
    ('lucas', 'cidade.jpg', 'voltando do curso', 28),
    ('bia', 'jardim.jpg', 'o jardim da escola tá lindo', 34),
    ('ana', 'montanhas.jpg', 'trilha da excursão, valeu a subida', 50),
    ('joao', 'festa.jpg', 'festa de fim de ano 🎉', 60),
    ('carla', 'praia.jpg', 'saudade das férias', 80),
    ('lucas', 'ceu-estrelado.jpg', 'céu da chácara, sem filtro', 96),
    ('bia', 'lago.jpg', 'manhã no lago', 120),
    ('ana', 'dunas.jpg', 'viagem de campo', 150),
    ('carla', 'aurora.jpg', 'um dia eu vejo uma de verdade ✨', 200),
]

# arquivo do post -> quem curtiu
CURTIDAS = {
    'por-do-sol.jpg': ['carla', 'ana', 'bia', 'joao'],
    'cafe.jpg': ['bruno', 'lucas', 'bia'],
    'vulcao.jpg': ['carla', 'bruno', 'bia', 'lucas', 'joao'],
    'cidade.jpg': ['ana', 'joao'],
    'jardim.jpg': ['carla', 'ana', 'lucas'],
    'montanhas.jpg': ['carla', 'bruno', 'bia', 'lucas', 'joao'],
    'festa.jpg': ['carla', 'ana', 'bruno', 'bia', 'lucas'],
    'praia.jpg': ['ana', 'bia', 'joao'],
    'ceu-estrelado.jpg': ['carla', 'bia'],
    'lago.jpg': ['carla', 'ana', 'lucas'],
    'dunas.jpg': ['bruno', 'joao'],
    'aurora.jpg': ['ana', 'bia', 'lucas', 'joao'],
}

# (arquivo do post, quem comentou, texto, quantas horas depois do post)
COMENTARIOS = [
    ('por-do-sol.jpg', 'carla', 'que céu!', 0.2),
    ('por-do-sol.jpg', 'joao', 'amanhã tem jogo?', 0.5),
    ('por-do-sol.jpg', 'bruno', 'tem sim, 16h', 0.8),
    ('cafe.jpg', 'bia', 'boa sorte na prova!', 0.5),
    ('cafe.jpg', 'lucas', 'esse coraçãozinho ficou perfeito', 1),
    ('vulcao.jpg', 'carla', 'foi o melhor da feira', 1),
    ('vulcao.jpg', 'lucas', 'vocês ganharam?', 2),
    ('vulcao.jpg', 'ana', 'segundo lugar 🥈', 2.5),
    ('jardim.jpg', 'ana', 'as flores amarelas são as minhas favoritas', 3),
    ('montanhas.jpg', 'bruno', 'minhas pernas até agora doendo', 2),
    ('montanhas.jpg', 'bia', 'vista incrível', 4),
    ('festa.jpg', 'carla', 'melhor festa do ano', 1),
    ('festa.jpg', 'bruno', 'quem fez a playlist?', 2),
    ('festa.jpg', 'bia', 'eu 😎', 2.2),
    ('praia.jpg', 'joao', 'leva eu na próxima', 5),
    ('ceu-estrelado.jpg', 'carla', 'dá pra ver a lua certinho', 3),
    ('lago.jpg', 'lucas', 'parece pintura', 6),
    ('aurora.jpg', 'ana', 'um dia a gente vai junto', 10),
]

# (quem mandou, texto, há quantos minutos)
MENSAGENS = [
    ('joao', 'bom dia, turma! 👋', 190),
    ('carla', 'bom diaa', 186),
    ('ana', 'alguém já começou o trabalho de Programação Web?', 150),
    ('lucas', 'eu! tô fazendo o chat com Socket.IO', 148),
    ('lucas', 'o broadcast é bem mais fácil do que parece', 147),
    ('ana', 'o meu deu erro no banco quando adicionei coluna nova 😅', 120),
    ('bia', 'tem que atualizar a tabela, senão o SQLite não acha a coluna', 118),
    ('bruno', 'quem vai no jogo de amanhã? 🏀', 60),
    ('joao', 'eu vou', 58),
    ('carla', 'vou levar a câmera 📸', 55),
    ('bia', 'postei foto do jardim lá no feed, olhem', 30),
    ('ana', 'ficou linda!', 25),
]


def _assinatura(caminho):
    """Tamanho + hash do conteúdo, para reconhecer cópias das imagens de exemplo."""
    with open(caminho, 'rb') as f:
        return os.path.getsize(caminho), hashlib.sha256(f.read()).hexdigest()


def limpar_copias_soltas(pasta_uploads, pasta_exemplos):
    """Apaga de static/uploads só as cópias das imagens de exemplo que nenhum post
    ou perfil usa (sobras de uma carga que deu erro). Fotos enviadas por usuários
    nunca são tocadas: o arquivo precisa ser idêntico a uma imagem de static/exemplos."""
    exemplos = {_assinatura(os.path.join(pasta_exemplos, f)) for f in os.listdir(pasta_exemplos)}
    em_uso = {p.imagem for p in Post.query.all()} | {u.foto for u in Usuario.query.all() if u.foto}
    removidos = 0
    for subpasta in ('', 'perfil'):
        pasta = os.path.join(pasta_uploads, subpasta)
        if not os.path.isdir(pasta):
            continue
        for nome in os.listdir(pasta):
            caminho = os.path.join(pasta, nome)
            if os.path.isfile(caminho) and nome not in em_uso and not nome.startswith('.') \
                    and _assinatura(caminho) in exemplos:
                os.remove(caminho)
                removidos += 1
    if removidos:
        print(f'[exemplos] {removidos} cópias soltas de imagens de exemplo removidas de static/uploads')


def carregar_exemplos(pasta_uploads):
    """Cria os dados de exemplo uma única vez. Devolve True se criou algo.
    Se algo der errado, desfaz tudo e o site abre normalmente, sem os exemplos."""
    if Usuario.query.filter_by(email=USUARIOS[0][2]).first():
        return False  # já foi carregado antes

    pasta_exemplos = os.path.join(os.path.dirname(pasta_uploads), 'exemplos')
    if not os.path.isdir(pasta_exemplos):
        print('[exemplos] pasta static/exemplos não encontrada; nada foi criado.')
        return False

    limpar_copias_soltas(pasta_uploads, pasta_exemplos)

    copiados = []
    try:
        _criar(pasta_uploads, pasta_exemplos, copiados)
        return True
    except Exception as erro:
        db.session.rollback()
        for caminho in copiados:   # não deixa imagens soltas para trás
            if os.path.exists(caminho):
                os.remove(caminho)
        print(f'[exemplos] não foi possível criar os dados de exemplo: {erro!r}')
        print('[exemplos] o site continua funcionando normalmente, só sem os exemplos.')
        return False


def _criar(pasta_uploads, pasta_exemplos, copiados):
    agora = datetime.now()

    def copiar(arquivo, subpasta=''):
        """Copia a imagem de exemplo para uploads com nome uuid4 (como um upload de verdade)."""
        extensao = arquivo.rsplit('.', 1)[1].lower()
        novo_nome = f'{uuid.uuid4()}.{extensao}'
        destino = os.path.join(pasta_uploads, subpasta)
        os.makedirs(destino, exist_ok=True)
        caminho = os.path.join(destino, novo_nome)
        shutil.copyfile(os.path.join(pasta_exemplos, arquivo), caminho)
        copiados.append(caminho)
        return novo_nome

    # Usuários (senha com hash scrypt, igual ao cadastro)
    usuarios = {}
    for apelido, nome, email, bio, foto, dias in USUARIOS:
        existente = Usuario.query.filter_by(email=email).first()
        if existente:
            usuarios[apelido] = existente
            continue
        u = Usuario(nome, email, generate_password_hash(SENHA_EXEMPLO, method='scrypt'))
        u.bio = bio
        u.foto = copiar(foto, 'perfil') if foto else None
        u.criado_em = agora - timedelta(days=dias)
        db.session.add(u)
        usuarios[apelido] = u
    db.session.flush()  # gera os ids

    # Posts
    posts = {}
    for apelido, arquivo, legenda, horas in POSTS:
        p = Post(copiar(arquivo), legenda, usuarios[apelido].id)
        p.data_post = agora - timedelta(hours=horas)
        db.session.add(p)
        posts[arquivo] = p
    db.session.flush()

    # Curtidas
    for arquivo, quem in CURTIDAS.items():
        for i, apelido in enumerate(quem):
            curtida = Curtida(usuarios[apelido].id, posts[arquivo].id)
            curtida.data = min(posts[arquivo].data_post + timedelta(minutes=10 * (i + 1)), agora)
            db.session.add(curtida)

    # Comentários
    for arquivo, apelido, texto, horas_depois in COMENTARIOS:
        c = Comentario(texto, usuarios[apelido].id, posts[arquivo].id)
        c.data = min(posts[arquivo].data_post + timedelta(hours=horas_depois), agora)
        db.session.add(c)

    # Mensagens do chat
    for apelido, texto, minutos in MENSAGENS:
        m = Mensagem(texto, usuarios[apelido].id)
        m.data = agora - timedelta(minutes=minutos)
        db.session.add(m)

    db.session.commit()
    print(f'[exemplos] criados {len(usuarios)} usuários, {len(posts)} posts, '
          f'{sum(len(v) for v in CURTIDAS.values())} curtidas, {len(COMENTARIOS)} comentários '
          f'e {len(MENSAGENS)} mensagens. Senha das contas de exemplo: {SENHA_EXEMPLO}')
