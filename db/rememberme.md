Registro de hábitos, saúde e condições no momento do cadastro
Decisão:
Todas essas informações serão armazenadas na tabela Observation

Serão diferenciadas pelo campo observation_type_concept_id = 'baseline'

O tipo da observação será determinado por observation_concept_id

Campos utilizados:
Campo	Exemplo
observation_concept_id	'sleep_quality', 'diet_habit'
value_as_concept_id	'sleeps_well', 'me_alimento_bem'
value_as_text	Texto livre (ex: comorbidades)
observation_date	Data do preenchimento
shared_with_provider	true / false


---
Personalizacao e protagonismo do paciente

Campo	Valor sugerido
observation_concept_id	"feels_good_with" ou "feels_bad_with" ou "activity_affected"
value_as_text	Ex: "Encontrar amigos", "Comer mal", "Limpar a casa"
observation_date	Data da escolha (ou data de criação do perfil)
observation_type_concept_id	"self_defined"
shared_with_provider	false por padrão (ou opcional se usuário quiser)

Observation.objects.create(
    person=person,
    observation_concept_id="feels_bad_with",
    value_as_text="Dormir mal",
    observation_type_concept_id="self_defined",
    observation_date=date.today(),
    shared_with_provider=False
)


Se quiser gerar gráficos semanais do que mais aparece, ou alertas baseados em repetições, essa estrutura te permite isso com simples GROUP BY.


1. Quando o usuário cria um hábito/tarefa personalizada
➡️ Você cria um novo Concept na tabela Concept.

concept_id	concept_name	domain_id
9999	Beber água	self_metric_scale
8888	Dormir bem	self_metric_bool

2. Você também cria valores possíveis, se quiser
concept_id	concept_name	domain_id
4001	1 vez	metric_value
4002	2 vezes	metric_value
4003	Sim	boolean
4004	Não	boolean

-- 📌 1. Criando conceitos para métricas personalizadas
INSERT INTO Concept (concept_id, concept_name, domain_id) VALUES
(9001, 'Beber água', 'self_metric_scale'),
(9002, 'Dormir bem', 'self_metric_boolean');

-- 📌 2. Criando conceitos para valores possíveis
INSERT INTO Concept (concept_id, concept_name, domain_id) VALUES
(4001, '1 vez', 'metric_value'),
(4002, '2 vezes', 'metric_value'),
(4003, 'Sim', 'boolean'),
(4004, 'Não', 'boolean');

-- 📌 3. Registrando observações (entradas do usuário)

-- Exemplo: Usuário 101 registrou que bebeu água 2 vezes hoje
INSERT INTO Observation (
  person_id,
  observation_concept_id,
  value_as_concept_id,
  observation_date,
  shared_with_provider,
  created_at,
  updated_at
) VALUES (
  101,
  9001,  -- Beber água
  4002,  -- 2 vezes
  CURRENT_DATE,
  false,
  CURRENT_TIMESTAMP,
  CURRENT_TIMESTAMP
);

-- Exemplo: Usuário 101 registrou que dormiu bem hoje
INSERT INTO Observation (
  person_id,
  observation_concept_id,
  value_as_concept_id,
  observation_date,
  shared_with_provider,
  created_at,
  updated_at
) VALUES (
  101,
  9002,  -- Dormir bem
  4003,  -- Sim
  CURRENT_DATE,
  false,
  CURRENT_TIMESTAMP,
  CURRENT_TIMESTAMP
);


✔️ Modelo recomendado: usar Note com note_type_concept_id = dica
Campo	Como usar para "Dicas"
note_id	PK
note_text	Texto da dica
note_date	Quando foi publicada (ou validade)
note_type_concept_id	Criar um Concept chamado health_tip ou educational_content
linkedProvider_id	pode ser null se for dica genérica
Se quiser marcar que o paciente leu a dica, você pode usar a mesma tabela Note e criar uma linha por pessoa com status de leitura, ou duplicar isso em Observation.

📘 Exemplo real:
➕ Concept:
sql
Copiar
Editar
INSERT INTO Concept (concept_id, concept_name, domain_id) VALUES
(8010, 'health_tip', 'note_type');
➕ Note:
sql
Copiar
Editar
INSERT INTO Note (
  note_id, linkedProvider_id, note_date, note_text, note_type_concept_id
) VALUES (
  DEFAULT, NULL, CURRENT_DATE, 'Beber água é essencial para o cérebro.', 8010
);
