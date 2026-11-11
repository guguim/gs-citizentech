from .textmatch import compact, min_substring_distance, tolerance_for

CIDADES_CONHECIDAS = (
    "Rio Branco", "Maceió", "Macapá", "Manaus", "Salvador", "Fortaleza", "Brasília",
    "Vitória", "Goiânia", "São Luís", "Cuiabá", "Campo Grande", "Belo Horizonte",
    "Belém", "João Pessoa", "Curitiba", "Recife", "Teresina", "Rio de Janeiro",
    "Natal", "Porto Alegre", "Porto Velho", "Boa Vista", "Florianópolis", "São Paulo",
    "Aracaju", "Palmas", "Guarulhos", "Osasco", "Santo André", "São Bernardo do Campo",
    "São Caetano do Sul", "Diadema", "Mauá", "Barueri", "Carapicuíba", "Campinas",
    "Santos", "Sorocaba", "Ribeirão Preto", "São José dos Campos", "Jundiaí",
    "Niterói", "Contagem", "Londrina", "Joinville", "Uberlândia",
)

CIDADES_NORMALIZADAS = tuple((compact(c), c) for c in CIDADES_CONHECIDAS)


def match_city(texto):
    alvo = compact(texto)
    if not alvo:
        return None
    melhor = None
    for normalizada, original in CIDADES_NORMALIZADAS:
        distancia = min_substring_distance(alvo, normalizada)
        if distancia > tolerance_for(len(normalizada)):
            continue
        chave = (distancia, -len(normalizada))
        if melhor is None or chave < melhor[0]:
            melhor = (chave, original)
    return melhor[1] if melhor else None
