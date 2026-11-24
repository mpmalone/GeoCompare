GeoCompare/
│
├── app.py
│
├── pages/
│   ├── 1_Play_Game.py
│   ├── 2_Game_Results.py
│   ├── 3_Player_Statistics.py
│   └── 4_About.py
│
├── src/
│   ├── game/
│   │   ├── game_engine.py
│   │   ├── question_generator.py
│   │   ├── scoring.py
│   │   └── difficulty.py
│   │
│   ├── database/
│   │   ├── connection.py
│   │   ├── entities.py
│   │   ├── statistics.py
│   │   ├── images.py
│   │   └── game_history.py
│   │
│   ├── data/
│   │   ├── import_data.py
│   │   ├── clean_data.py
│   │   └── validate_data.py
│   │
│   └── utils/
│       ├── formatting.py
│       └── helpers.py
│
├── data/
│   ├── raw/
│   │   ├── countries.csv
│   │   ├── cities.csv
│   │   ├── mountains.csv
│   │   ├── rivers.csv
│   │   └── lakes.csv
│   │
│   └── processed/
│       ├── entities.csv
│       ├── statistics.csv
│       └── entity_statistics.csv
│
├── sql/
│   ├── migrations/
│   │   ├── 001_create_entity_types.sql
│   │   ├── 002_create_entities.sql
│   │   ├── 003_create_statistics.sql
│   │   ├── 004_create_entity_statistics.sql
│   │   ├── 005_create_entity_images.sql
│   │   ├── 006_create_profiles.sql
│   │   ├── 007_create_game_sessions.sql
│   │   ├── 008_create_game_questions.sql
│   │   └── 009_create_player_answers.sql
│   │
│   └── seed_data.sql
│
├── tests/
│   ├── test_question_generator.py
│   ├── test_game_engine.py
│   ├── test_scoring.py
│   ├── test_data_validation.py
│   └── test_image_management.py
│
├── .env
├── .gitignore
├── requirements.txt
├── README.md
└── LICENSE


pages/	Streamlit screens and user interface
src/game/	Question generation, game rules and scoring
src/database/	Supabase database queries
src/data/	Importing, cleaning and validating datasets
src/utils/	Reusable helper functions
data/raw/	Original downloaded datasets
data/processed/	Cleaned datasets ready for import
sql/migrations/	Database creation and structural changes
tests/	Automated testing



2. Table-by-table breakdown
A. Geographical data
These tables contain the information that powers the game.

entity_types

Defines the different types of geographical entities.
Field	Type	Example
entity_type_id	integer	1
name	text	Mountain
description	text	Mountainous geographical features

Example records:
- Country
- City
- Mountain
- River
- Lake
- Island

entities

Stores the individual geographical entities.
Field	Type	Example
entity_id	integer	1
entity_type_id	FK	3
name	text	Mount Everest
country	text	Nepal / China
description	text	World's highest mountain

You could eventually add coordinates, continent, region and other geographical attributes.

statistics

Defines the numerical measurements used in comparisons.
Field	Type	Example
statistic_id	integer	1
name	text	Elevation
unit	text	metres
comparison_label	text	higher

Example records:
Statistic	Unit	Comparison wording
Elevation	metres	Higher / Lower
Population	people	More / Fewer
Area	km²	Larger / Smaller
Length	km	Longer / Shorter
Population density	people/km²	Higher / Lower
Depth	metres	Deeper / Shallower

I'd keep the comparison wording in this table so the game can generate questions automatically.

entity_statistics

This is one of the most important tables.

It connects geographical entities to their numerical statistics.
entity_id	statistic_id	value	reference_date
1	1	8849	2020-01-01
2	1	5895	2020-01-01
3	2	37000000	2024-01-01

For example, Mount Everest has an elevation of 8,849 metres.

The same entity could have multiple statistics, and a statistic could have multiple historical records.

I'd also include:
- source – where the value originated.
- source_url – link to the original dataset.
- reference_date – when the measurement applies.
- last_updated – when you imported or updated the record.
This is particularly important for population, rainfall and other changing statistics.
B. Image management
entity_images

This is the new table specifically for photographs and other visual assets.
Field	Type	Purpose
image_id	integer	Unique image identifier
entity_id	FK	Associated geographical entity
storage_path	text	Image location in Supabase Storage
source	text	Wikimedia, Unsplash, etc.
source_url	text	Original image page
photographer	text	Creator's name
licence	text	Licence type
licence_url	text	Link to licence
attribution	text	Required credit
is_primary	boolean	Main image for game
date_added	timestamp	Date added

I'd use a Supabase Storage bucket called entity-images.

For example:
entity-images/
    mountains/
        mount-everest-01.jpg
        mount-kilimanjaro-01.jpg
    countries/
        australia-01.jpg
    rivers/
        nile-01.jpg


The storage_path field would contain the file's path, not necessarily a permanent public URL.

That gives you flexibility if you change storage arrangements later.

I'd also include an image approval status, such as pending, approved or rejected, so you can verify image permissions before publishing them.
C. Player and game data
I'd include these tables in the overall design, although you don't need to implement all player functionality immediately.

profiles

Stores public player information and connects to Supabase Authentication.
Field	Type
player_id	UUID
username	text
created_at	timestamp

The player_id should reference Supabase's auth.users table.

game_sessions

Records individual games.
Field	Type
session_id	UUID
player_id	UUID
score	integer
best_streak	integer
total_questions	integer
started_at	timestamp
completed_at	timestamp

game_questions

Records each comparison presented during a game.

This table is particularly important because it stores the values that were used when the question was generated.
Field	Example
question_id	Unique question ID
session_id	Associated game
entity_a_id	Mount Everest
entity_b_id	Mount Kilimanjaro
statistic_id	Elevation
comparison_operator	higher
entity_a_value	8849
entity_b_value	5895
correct_entity_id	Mount Everest

The player wouldn't see the numerical values until after submitting an answer.

player_answers

Records the player's response.
Field	Example
answer_id	Unique answer ID
question_id	Associated question
selected_entity_id	Mount Everest
is_correct	True
response_time	3.5 seconds
answered_at	Timestamp

Separating questions from answers means you can analyse the questions presented and how players responded to them.