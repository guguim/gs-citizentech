import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Address:
    logradouro: str
    numero: str
    complemento: str
    bairro: str
    cidade: str
    uf: str
    cep: str


@dataclass(frozen=True)
class Customer:
    nome: str
    endereco: Address


FIRST_NAMES = [
    "Ana", "Bruno", "Carla", "Diego", "Elisa", "Fábio", "Gabriela", "Henrique",
    "Isabela", "João", "Karina", "Lucas", "Mariana", "Nelson", "Olívia", "Paulo",
    "Renata", "Sérgio", "Tatiana", "Vinícius",
]

SURNAMES = [
    "Almeida", "Barbosa", "Cardoso", "Domingues", "Esteves", "Ferraz", "Gonçalves",
    "Horta", "Ibrahim", "Junqueira", "Klein", "Lacerda", "Menezes", "Nogueira",
    "Oliveira", "Pacheco", "Queiroz", "Ramos", "Siqueira", "Teixeira",
]

STREET_TYPES = ["Rua", "Avenida", "Alameda", "Travessa"]

STREET_NAMES = [
    "das Acácias", "Santos Dumont", "Dom Pedro II", "Sete de Setembro",
    "Marechal Deodoro", "das Palmeiras", "João Batista de Oliveira",
    "Padre Anchieta", "Rio Branco", "XV de Novembro", "dos Ipês", "Tiradentes",
    "Machado de Assis", "Rui Barbosa", "das Flores", "Castro Alves",
    "Barão de Itapetininga", "Conselheiro Nébias", "José Bonifácio",
    "Presidente Vargas", "Cardeal Arcoverde", "Joaquim Nabuco", "Carlos Gomes",
    "Voluntários da Pátria",
]

NEIGHBORHOODS = [
    "Centro", "Jardim Primavera", "Vila Mariana", "Vila Nova", "Jardim das Rosas",
    "Santa Cecília", "Bela Vista", "Parque São Jorge", "Jardim América",
    "Vila Industrial", "Mooca", "Pinheiros", "Tatuapé", "Liberdade", "Itaim Bibi",
    "Jardim Paulista", "Vila Esperança", "Cidade Jardim",
]

CITIES = [
    ("São Paulo", "SP", 1000, 5999, 6),
    ("Guarulhos", "SP", 7000, 7399, 1),
    ("Osasco", "SP", 6000, 6299, 1),
    ("Santo André", "SP", 9000, 9299, 1),
    ("São Bernardo do Campo", "SP", 9600, 9899, 1),
    ("Campinas", "SP", 13000, 13139, 1),
    ("Rio de Janeiro", "RJ", 20000, 23799, 1),
    ("Belo Horizonte", "MG", 30000, 31999, 1),
    ("Curitiba", "PR", 80000, 82999, 1),
]

COMPLEMENT_MODELS = [
    "", "", "Apto {n}", "Bloco {bloco} Apto {n}", "Casa {n}", "Fundos", "Sala {n}",
]


def random_complement(rng):
    modelo = rng.choice(COMPLEMENT_MODELS)
    return modelo.format(n=rng.randint(1, 180), bloco=rng.choice("ABCD"))


def generate_address(rng):
    cidade, uf, minimo, maximo, _ = rng.choices(CITIES, weights=[c[4] for c in CITIES])[0]
    cep = f"{rng.randint(minimo, maximo):05d}-{rng.randint(1, 899):03d}"
    return Address(
        logradouro=f"{rng.choice(STREET_TYPES)} {rng.choice(STREET_NAMES)}",
        numero=str(rng.randint(1, 2999)),
        complemento=random_complement(rng),
        bairro=rng.choice(NEIGHBORHOODS),
        cidade=cidade,
        uf=uf,
        cep=cep,
    )


def generate_customer(rng):
    nome = f"{rng.choice(FIRST_NAMES)} {rng.choice(SURNAMES)} {rng.choice(SURNAMES)}"
    return Customer(nome=nome, endereco=generate_address(rng))
