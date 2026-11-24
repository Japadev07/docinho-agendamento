# Docinho — Sistema de Agendamento de Festas

Implementação em Python (Programação Orientada a Objetos) do sistema de agendamento
da **Docinho Recreação Infantil**, a partir dos requisitos e do Diagrama de Classes
da TED 03 de Análise e Engenharia de Sistemas (SRS 1.1, PRD e Documento de Visão).

**Integrantes:** Everton Felipe Cirqueira da Silva e Fernando Lemke da Silveira
— Centro Universitário Unibalsas.

O sistema é de uso interno pela gestora (Bruna): cadastra contratantes, festas e
recreadores, mostra a agenda, sinaliza conflitos de escala, acompanha valores
(sem processar pagamentos) e organiza os avisos (o envio pelo WhatsApp é manual).

## Requisitos

* Python 3.9 ou superior (testado com 3.13).
* Nenhuma dependência para executar o sistema (só a biblioteca padrão).
* `pytest` para rodar os testes.

## Instalação

```bash
# 1) (opcional, recomendado) criar o ambiente virtual
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux / macOS

# 2) instalar as dependências de teste
pip install -r requirements.txt
```

Não é preciso instalar o pacote para usar: `principal.py` e os testes já encontram a pasta `src/`.
Se preferir instalar, use `pip install -e ".[dev]"` (cria também o comando `docinho`).

## Como iniciar a aplicação

```bash
python principal.py                  # abre o menu; dados em dados/docinho.json
python principal.py --dados outro.json
python -m docinho                    # equivalente, se o pacote estiver instalado
```

Os dados ficam em `dados/docinho.json` (criado no primeiro uso). Também é possível
escolher o arquivo com a variável de ambiente `DOCINHO_DADOS`.

### Carga inicial (dados de demonstração)

```bash
python scripts/carga_inicial.py            # cria dados/docinho.json com 6 recreadores, 3 contratantes e 3 festas
python scripts/carga_inicial.py --forcar   # apaga e recria do zero
```

A carga usa `dados/dados_iniciais.json` (dados fictícios; as datas das festas são relativas ao dia da execução).

## Como executar os testes

```bash
python -m pytest
```

Todos os testes devem passar (233 testes, cobertura de ~96% do código-fonte).
Para ver a cobertura: `pip install coverage` e `coverage run --source=src/docinho -m pytest` seguido de `coverage report -m`.

## Estrutura do projeto

```
docinho/
├── README.md
├── pyproject.toml / requirements.txt
├── principal.py                  # atalho para iniciar o sistema
├── src/docinho/
│   ├── modelos/                  # classes do Diagrama de Classes (POO)
│   │   ├── contratante.py  recreador.py  festa.py
│   │   ├── pagamento.py (RegistroPagamento)  lembrete.py  detalhes.py (DetalhesComplementares)
│   │   └── base.py (classe abstrata)  enumeracoes.py  faixa_etaria.py  atividade.py  dimensionamento.py
│   ├── servicos/                 # regras de negócio e casos de uso
│   │   ├── servico_contratante.py  servico_recreador.py  servico_festa.py
│   │   ├── servico_escala.py  servico_financeiro.py  servico_lembrete.py
│   │   └── regras_aviso.py (polimorfismo)  servico_agenda.py  servico_resumo.py
│   ├── persistencia/             # repositórios JSON/memória, armazenamento e transações
│   ├── sistema.py                # fachada que monta os serviços
│   └── menu.py                   # menu em português
├── tests/                        # suíte pytest (modelos, serviços, persistência, menu)
├── dados/dados_iniciais.json     # carga inicial
├── scripts/carga_inicial.py
└── documentos/RASTREABILIDADE.md # UML → código, requisitos → testes, alterações justificadas
```

## Como o código aplica a POO

| Conceito | Onde |
|---|---|
| **Encapsulamento** | atributos privados com `@property` e validação nos setters (`Contratante`, `Recreador`, `Festa`, `DetalhesComplementares`...); listas internas expostas como tuplas |
| **Abstração** | `EntidadeBase` (ABC com `para_dicionario`, `de_dicionario`, `__str__`), `Repositorio` (ABC de persistência), `RegraDeAviso` (ABC) |
| **Herança** | `Contratante`, `Recreador` e `Festa` herdam de `EntidadeBase`; `RepositorioJSON` e `RepositorioMemoria` herdam de `Repositorio` |
| **Polimorfismo** | `AvisoConfirmacao`, `AvisoQuatorzeDias` e `AvisoSeteDias` sobrescrevem `RegraDeAviso.gerar`; o `ServicoLembrete` as usa sem distinguir uma da outra; cada entidade sobrescreve `__str__`/`para_dicionario` |
| **Métodos especiais** | `__str__`, `__repr__`, `__eq__` (Contratante, Recreador, FaixaEtaria), `__lt__` (Festa, ordena a agenda), `__contains__` (`7 in FaixaEtaria(5, 9)`), `__len__`, `__iter__` e `__getitem__` (Agenda) |
| **Relacionamentos** | associação (Contratante–Festa, Festa–Recreador) e composição (Festa controla RegistroPagamento, Lembrete e DetalhesComplementares), ver `documentos/RASTREABILIDADE.md` |

## Principais regras implementadas

* **RF-01** cadastro e busca de contratante por nome (sem acento/maiúsculas) ou telefone.
* **RF-02** festa só é registrada com todos os campos obrigatórios (`CampoObrigatorioErro` lista o que falta). Brindes e deslocamento: informar "não se aplica" quando não houver.
* **RF-03** agenda ordenada, filtros por período/situação: confirmada, realizada, quitada, cancelada.
* **RF-04 / RN-05 / RN-07** conflito de escala (sobreposição, intervalo menor que 60 min, recreador indisponível) gera **alerta**; a decisão final é da gestora (`forcar=True`). Festas simultâneas com equipes distintas são permitidas.
* **RN-06** dimensionamento da equipe exatamente como informado no formulário, sem extrapolar.
* **RF-06 / RN-02** entrada prevista = 50%; saldo = valor combinado − pagamentos; a data só fica reservada após a entrada. R$ 1.000,00 → entrada R$ 500,00, saldo R$ 500,00, após quitação R$ 0,00.
* **RN-03** cancelamento retém o valor pago por 1 ano.
* **RN-08** a primeira contratação de cada contratante recebe um brinde.
* **RF-08 / RN-09** avisos: na confirmação, 14 dias antes (ou imediato se faltarem menos de 14 dias) e repetição 7 dias antes; remarcação refaz os avisos. O sistema **não envia** mensagens: a gestora marca o aviso como enviado.
* **RF-09** resumo do evento com contratante, programação, equipe, valores, avisos e alertas.
* **RNF-03** gravação em transação: se a gravação falhar, o pagamento/alteração é desfeito (saldo nunca diverge). Arquivo gravado de forma atômica.
* **RNF-04** cópia de segurança a cada 24 h (feita ao abrir o sistema) e restauração da última cópia válida.

## Tratamento de situações inválidas

Todas as falhas esperadas herdam de `DocinhoErro` (`ValidacaoErro`, `CampoObrigatorioErro`,
`RegraDeNegocioErro`, `ConflitoEscalaErro`, `TransicaoInvalidaErro`, `NaoEncontradoErro`,
`PersistenciaErro`) e as mensagens são em português.

## Limitações conhecidas

* Interface de texto (terminal). A SRS prevê uso pelo celular (iPhone/Safari, RNF-01 e RNF-05) e
  autenticação (RNF-02); isso fica para um futuro front-end e está registrado em `documentos/RASTREABILIDADE.md`.
* Pendências que a própria SRS deixa para confirmar com a representante (ex.: "não se aplica",
  linha de 10 a 12 anos do dimensionamento) foram implementadas de forma literal e documentadas.
