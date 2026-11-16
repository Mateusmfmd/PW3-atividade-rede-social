# Instância do SQLAlchemy e classes Usuario e Post
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
from datetime import datetime

db = SQLAlchemy()


def atualizar_banco():
    """Cria as tabelas e adiciona as colunas que faltam num banco antigo,
    sem precisar apagar o arquivo .sqlite3 (os dados continuam lá)."""
    db.create_all()

    inspetor = inspect(db.engine)
    for tabela in db.metadata.sorted_tables:
        existentes = {coluna['name'] for coluna in inspetor.get_columns(tabela.name)}
        for coluna in tabela.columns:
            if coluna.name not in existentes:
                tipo = coluna.type.compile(dialect=db.engine.dialect)
                db.session.execute(text(f'ALTER TABLE {tabela.name} ADD COLUMN {coluna.name} {tipo}'))
                print(f'[banco] coluna adicionada: {tabela.name}.{coluna.name}')

    # Usuários antigos ficam com a data de cadastro de hoje
    agora = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    db.session.execute(text('UPDATE usuario SET criado_em = :agora WHERE criado_em IS NULL'), {'agora': agora})
    db.session.commit()


class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha = db.Column(db.String(255), nullable=False)
    # Extras: foto de perfil (arquivo em static/uploads/perfil), bio e data de cadastro
    foto = db.Column(db.String(255), nullable=True)
    bio = db.Column(db.String(160), nullable=True)
    criado_em = db.Column(db.DateTime, default=datetime.now)

    # Relacionamento 1 para N com Post
    posts = db.relationship('Post', backref='autor', lazy=True)

    def __init__(self, nome, email, senha):
        self.nome = nome
        self.email = email
        self.senha = senha


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    imagem = db.Column(db.String(255), nullable=False)
    legenda = db.Column(db.String(255), nullable=True)
    data_post = db.Column(db.DateTime, default=datetime.now)

    # Chave estrangeira
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)

    # Extras: curtidas e comentários são apagados junto com o post
    curtidas = db.relationship('Curtida', backref='post', lazy=True, cascade='all, delete-orphan')
    comentarios = db.relationship('Comentario', backref='post', lazy=True, cascade='all, delete-orphan',
                                  order_by='Comentario.data')

    def __init__(self, imagem, legenda, usuario_id):
        self.imagem = imagem
        self.legenda = legenda
        self.usuario_id = usuario_id


# Extra: tabela associativa de curtidas (Usuario N <-> N Post)
class Curtida(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    data = db.Column(db.DateTime, default=datetime.now)  # quando curtiu

    # Cada usuário curte o mesmo post no máximo uma vez
    __table_args__ = (db.UniqueConstraint('usuario_id', 'post_id'),)

    def __init__(self, usuario_id, post_id):
        self.usuario_id = usuario_id
        self.post_id = post_id


# Extra: comentários nos posts
class Comentario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    texto = db.Column(db.String(300), nullable=False)
    data = db.Column(db.DateTime, default=datetime.now)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)

    autor = db.relationship('Usuario')

    def __init__(self, texto, usuario_id, post_id):
        self.texto = texto
        self.usuario_id = usuario_id
        self.post_id = post_id


# Extra: histórico do chat (quem chega vê as últimas mensagens)
class Mensagem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    texto = db.Column(db.String(500), nullable=False)
    data = db.Column(db.DateTime, default=datetime.now)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)

    autor = db.relationship('Usuario')

    def __init__(self, texto, usuario_id):
        self.texto = texto
        self.usuario_id = usuario_id
