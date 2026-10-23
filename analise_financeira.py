"""Avaliação de viabilidade para resgate de passagens."""


def analisar_viabilidade(saldo_milhas: int) -> str:
    """Retorna um diagnóstico informal a partir do saldo de milhas."""
    if saldo_milhas < 0:
        raise ValueError("O saldo de milhas não pode ser negativo.")

    if saldo_milhas == 0:
        return "Destino recomendado: ficar em casa."

    if saldo_milhas < 10_000:
        return "Destino recomendado: rodoviária mais próxima."

    return "Parabéns! Agora só falta o dinheiro para o hotel."


if __name__ == "__main__":
    print(analisar_viabilidade(0))
