"""
knowledge.py — SST AI knowledge engine
=======================================
Class 9, Social Science, NCERT "Understanding Society: India and Beyond"
(2026-27 edition), Part 1.

WHAT THIS FILE IS
------------------
This is the knowledge engine behind SST AI's Social Science tutor. It is
built on a small, hand-checked knowledge base (KB) drawn ONLY from the
actual NCERT Class 9 Social Science 2026-27 PDF chapters that were supplied
and read:

    Ch.1  Understanding Social Science
    Ch.2  Shaping of the Earth's Surface            (Geography)
    Ch.3  Atmosphere and Climate                    (Geography)
    Ch.4  Early Humans and Beginning of Civilisation (History)
    Ch.5  State and Society up to 1000 CE           (History)
    Ch.6  Democracy                                 (Political Science)
    Ch.7  Elections                                 (Political Science)
    Ch.8  Building Blocks in Economics:
          The Problem of Choice                     (Economics)
    Ch.9  The Price Puzzle: What Drives the Market  (Economics)

Coverage is honest, not uniform. No fact in this file was invented to
"fill in" a chapter — where the source material did not explicitly discuss
something, that field is simply absent from the topic, and the engine
falls back to the closest real content rather than hallucinating.

WHAT "1 LAKH QUESTIONS" MEANS HERE
-----------------------------------
This file stores ~35 hand-checked TOPICS (not rows of questions), each with
definition / short / medium / long / short_note fields (and importance /
features / causes / effects where the textbook supports them). The engine
below understands EVERY common way of asking about those topics — what/
define/explain/why/how/who/when/where/which, short note, 1-5 marks, "in one
line", "in detail", comparisons, examples, quizzes, Hinglish, typos, polite
and casual wrappers — and iter_supported_questions() generates well over
100,000 distinct question phrasings from them. self_test() runs all of them
through the real resolver and reports accuracy; export_question_bank() writes
them to a CSV. It is 1 lakh+ WAYS OF ASKING, not 1 lakh different facts:
inventing facts would break this project's accuracy rule (see below).

It also has a conversation layer: greetings, thanks, bye, help, topic list,
who-made-you, study tips, and so on.

HOW IT WORKS (question -> answer pipeline)
-------------------------------------------
    raw query
        -> mode detection      (short / medium / long / short_note / definition)
        -> question-type detection (definition / importance / features /
                                     causes / effects / general)
        -> topic phrase extraction (strip mode/type/stopwords)
        -> topic matching       (exact -> alias/keyword overlap -> fuzzy)
        -> field selection      (pick the KB field matching the question type,
                                  falling back gracefully if that field
                                  doesn't exist for this topic)
        -> answer string

FLASK INTEGRATION
------------------
    from knowledge import answer
    answer("what is democracy?")   # -> str, always

`answer()` never raises for a normal string input and always returns a
plain Python string (never None, never a tuple), so it drops straight into
an existing Flask route with no other changes needed.

ACCURACY / NEUTRALITY NOTES
-----------------------------
- All facts, figures, dates, and definitions below are taken from the
  supplied NCERT PDF text, not invented or guessed.
- Political-science / civics content (democracy, elections) is kept
  strictly textbook-descriptive: no ranking or opinion on parties,
  leaders, candidates or ideologies, and no promises made outside what
  the textbook itself states.
- If the engine can't confidently match a query to a KB topic, it says so
  plainly instead of guessing (see FALLBACK_MESSAGE below) — it never
  claims coverage it doesn't have.
"""

from __future__ import annotations
import re
import difflib
import functools


# ---------------------------------------------------------------------------
# 0. PROJECT / CREATOR METADATA
# ---------------------------------------------------------------------------
# Do not change these creator details.

CREATOR_INFO = {
    "creator_name": "Sahil",
    "class": "9",
    "school": "Daffodils Public School",
    "academic_year": "2026-27",
    "project_name": "SST AI",
    "project_type": "Class 9 Social Science AI Tutor",
}

PROJECT_INFO = {
    "name": "SST AI",
    "creator": "Sahil",
    "class": "9",
    "school": "Daffodils Public School",
    "academic_year": "2026-27",
    "purpose": "Class 9 Social Science learning assistant",
    "subjects": [
        "History",
        "Geography",
        "Political Science",
        "Economics",
    ],
    "chapters": [
        "1. Understanding Social Science",
        "2. Shaping of the Earth's Surface",
        "3. Atmosphere and Climate",
        "4. Early Humans and Beginning of Civilisation",
        "5. State and Society up to 1000 CE",
        "6. Democracy",
        "7. Elections",
        "8. Building Blocks in Economics: The Problem of Choice",
        "9. The Price Puzzle: What Drives the Market",
    ],
    "answer_modes": [
        "short",
        "medium",
        "long",
        "short_note",
        "definition",
    ],
}


# ---------------------------------------------------------------------------
# 1. KNOWLEDGE BASE
# ---------------------------------------------------------------------------
# KB[topic_key] = {
#     "chapter":     "N. Chapter Title",
#     "aliases":     [alternate ways a student might name/ask this topic],
#     "keywords":    [extra bag-of-words used only to widen matching],
#     "definition":  "one-line textbook-style meaning",
#     "short":       "1-2 sentence answer",
#     "medium":      "one paragraph answer (DEFAULT mode)",
#     "long":        "detailed, Class-9-level explanation",
#     "short_note":  "exam-style bullet points",
#     # optional, only present where the textbook explicitly frames it:
#     "importance":  "why this topic/thing matters",
#     "features":    [list of key features/principles/questions],
#     "causes":      "what causes this",
#     "effects":     "what results from this",
# }

KB = {'social_science': {'chapter': '1. Understanding Social Science',
                    'aliases': ['what is social science',
                                'define social science',
                                'meaning of social science'],
                    'definition': 'The systematic study of human society and how '
                                  'people, institutions, and the environment interact.',
                    'short': 'Social Science is the systematic study of human society '
                             '— how people live together, why events happen, and how '
                             'the past and present shape each other.',
                    'medium': 'Social Science is the systematic study of human '
                              'society. It explains not just what happened or where '
                              'things are located, but also why events occur, how '
                              'people live together, how environments influence life, '
                              'how governments function, how economies operate, and '
                              'how the past and present together shape the world. '
                              'Unlike Physics, Chemistry or Biology, which study the '
                              'natural world, Social Science focuses on society, '
                              'institutions, cultures, and human interactions.',
                    'long': 'Human beings live in societies and depend on each other. '
                            'Their lives are shaped by the environment, institutions, '
                            'economic activity, and traditions passed down through '
                            'generations — understanding these connections is the '
                            'foundation of Social Science. Even a simple daily routine '
                            '(the house you live in, the food you eat, the roads you '
                            'use, the school you attend) rests on systems of '
                            'governance, production, cooperation, and environment. '
                            'Social Science asks why differences exist between places '
                            'and communities (why some live in cities and others in '
                            'villages, why regions farm or industrialise, why floods '
                            'hit some areas more than others) and seeks answers '
                            'through observation, evidence, and logical reasoning. '
                            'This spirit of inquiry has deep roots in Indian '
                            'traditions too — ideas like the Pañchamahābhūtas (five '
                            "elements) and vasudhaiva kuṭumbakam ('the world is one "
                            "family') reflect early attempts to understand nature and "
                            "interdependence, while Kauṭilya's Arthaśhāstra (~2,300 "
                            'years ago) shows systematic thinking about governance and '
                            'economy well before modern academic disciplines existed. '
                            'Studying Social Science today matters because it helps '
                            'citizens understand how systems around them work, '
                            'participate responsibly in democracy, think critically '
                            'about shared challenges like climate change and urban '
                            'growth, and connect the past, present and future to make '
                            'wiser choices.',
                    'short_note': '• Social Science = systematic study of human '
                                  'society (what, where, why, how).\n'
                                  '• Differs from natural sciences '
                                  '(Physics/Chemistry/Biology study nature; Social '
                                  'Science studies society & human interaction).\n'
                                  '• Indian roots: Pañchamahābhūtas, vasudhaiva '
                                  'kuṭumbakam, Arthaśhāstra (Kauṭilya, ~2,300 yrs '
                                  'ago).\n'
                                  '• Grades 9–10 draw on 4 core disciplines: '
                                  'Geography, History, Political Science, Economics (+ '
                                  'Sociology, Philosophy, Anthropology, Psychology in '
                                  'later grades).\n'
                                  '• Importance: builds respect for diversity, '
                                  'informed citizenship, critical thinking, and links '
                                  'past→present→future.',
                    'keywords': ['define',
                                 'each',
                                 'environment',
                                 'events',
                                 'happen',
                                 'human',
                                 'institutions',
                                 'interact',
                                 'live',
                                 'meaning',
                                 'other',
                                 'past',
                                 'people',
                                 'present',
                                 'science',
                                 'shape',
                                 'social',
                                 'society',
                                 'study',
                                 'systematic',
                                 'together',
                                 'what']},
 'four_disciplines': {'chapter': '1. Understanding Social Science',
                      'aliases': ['four disciplines of social science',
                                  'branches of social science',
                                  'geography history political science economics'],
                      'definition': 'The four core disciplines of Social Science in '
                                    'Grades 9–10: Geography, History, Political '
                                    'Science, and Economics.',
                      'short': 'Social Science in Grades 9–10 is built on four core '
                               'disciplines: Geography, History, Political Science, '
                               'and Economics.',
                      'medium': 'Human society is too complex for one subject to '
                                'explain fully — a drought, for instance, affects '
                                "crops (environment/Geography), farmers' incomes "
                                '(Economics), government relief (Political Science), '
                                'and migration (society/History). So Social Science '
                                'draws on four core disciplines in Grades 9–10: '
                                'Geography (Earth, environments, and people-place '
                                'relationships), History (the human past and how '
                                'societies change), Political Science (governance, '
                                'power, rights and responsibilities), and Economics '
                                '(production, distribution and use of resources).',
                      'long': 'Each discipline asks a different question about the '
                              'same society:\n'
                              '• Geography — studies location/distribution of places '
                              'and people, and how people interact with the natural '
                              'environment; uses maps, GIS, atlases, infographics.\n'
                              '• History — studies the human past through sources: '
                              'literary (travelogues, manuscripts), archaeological '
                              '(monuments, artefacts), epigraphic (inscriptions), '
                              'numismatic (coins); relies increasingly on empirical '
                              'evidence (carbon-14 dating, genetics).\n'
                              '• Political Science — studies constitutions, '
                              'governments, institutions, and how power is exercised, '
                              'shared, and regulated (e.g., Panchayati Raj as '
                              'grassroots democracy).\n'
                              '• Economics — studies how individuals, enterprises and '
                              'governments decide to use limited resources; connects '
                              'to well-being, equity and justice, not just markets.\n'
                              'Other related fields (Sociology, Philosophy, '
                              'Anthropology, Psychology) are introduced in higher '
                              'grades. All four disciplines are interconnected and '
                              'together give a holistic view of society.',
                      'short_note': '• 4 core disciplines (Gr 9–10): Geography, '
                                    'History, Political Science, Economics.\n'
                                    '• Geography → space/environment/people; tools: '
                                    'maps, GIS, atlases.\n'
                                    '• History → human past; sources: literary, '
                                    'archaeological, epigraphic, numismatic; modern '
                                    'method = empirical evidence.\n'
                                    '• Political Science → governance, power, rights, '
                                    'institutions.\n'
                                    '• Economics → production, distribution, '
                                    'resource-use, well-being.\n'
                                    '• Later grades add: Sociology, Philosophy, '
                                    'Anthropology, Psychology.',
                      'keywords': ['9–10',
                                   'branches',
                                   'built',
                                   'core',
                                   'disciplines',
                                   'economics',
                                   'four',
                                   'geography',
                                   'grades',
                                   'history',
                                   'political',
                                   'science',
                                   'social']},
 'plate_tectonics': {'chapter': "2. Shaping of the Earth's Surface",
                     'aliases': ['plate tectonics',
                                 'tectonic plates',
                                 'what causes earthquakes'],
                     'definition': 'The theory (proposed by W.J. Morgan) that the '
                                   "Earth's crust is broken into large and small "
                                   'tectonic plates that move over the semi-molten '
                                   'mantle beneath them.',
                     'short': "Plate tectonics is the theory that the Earth's outer "
                              'layer is broken into several tectonic plates that move '
                              'slowly, causing mountains, earthquakes and volcanoes.',
                     'medium': 'The Earth is made up of crust, mantle and core. The '
                               'crust plus the upper mantle form the lithosphere, '
                               'broken into large and small tectonic plates that move '
                               'slowly over the semi-molten asthenosphere below, '
                               'driven by convection currents. Movement at plate '
                               'boundaries produces mountains, earthquakes and '
                               'volcanoes; India lies partly on the Indo-Australian '
                               'plate, making the Himalayan and north-eastern regions '
                               'earthquake-prone.',
                     'long': 'The Earth has three main layers — crust, mantle, and '
                             'core. The crust plus the upper mantle form the rigid '
                             'lithosphere, which is broken into large and small '
                             'tectonic plates (e.g., North American, South American, '
                             'Indo-Australian, African, Eurasian, Pacific, Antarctic '
                             'plates). These plates float on the semi-molten '
                             'asthenosphere below them and move due to convection '
                             'currents in the mantle: heat from the core causes molten '
                             'mantle material to rise while cooler material sinks, and '
                             'this continuous movement pushes and pulls the plates '
                             'above it. Where plates meet (plate boundaries), '
                             'collisions, separations, or sliding produce major '
                             'landforms and natural hazards — fold mountains form '
                             'where continental plates collide, while earthquakes and '
                             'volcanoes occur along many plate boundaries. India lies '
                             'partly on the Indo-Australian plate, which is why parts '
                             'of the country (especially the Himalayan region and the '
                             'north-east) are earthquake-prone.',
                     'short_note': 'Structure: 3 main layers — crust, mantle, core; '
                                   'crust + upper mantle = lithosphere (broken into '
                                   'tectonic plates); below it = semi-molten '
                                   'asthenosphere.\n'
                                   '3 plate boundary types: Convergent (plates collide '
                                   '— continental+continental = fold mountains e.g. '
                                   'Himalaya; oceanic+continental = oceanic plate '
                                   'sinks → volcanoes & earthquakes), Divergent '
                                   '(plates move apart — magma rises, new crust forms, '
                                   'e.g. Mid-Atlantic Ridge), Transform (plates slide '
                                   'past each other — mainly earthquakes, e.g. San '
                                   'Andreas Fault).\n'
                                   'Given by: W.J. Morgan.\n'
                                   "India's risk: lies partly on the Indo-Australian "
                                   'plate → earthquake risk, especially Himalayan and '
                                   'north-eastern states.',
                     'causes': 'Convection currents in the mantle: heat from the '
                               "Earth's core causes molten material in the mantle to "
                               'rise while cooler material sinks, and this continuous '
                               'circulation pushes and pulls the rigid tectonic plates '
                               'above it, causing them to move a few centimetres per '
                               'year.',
                     'effects': 'Plate movement produces mountains, valleys, ocean '
                                'basins, volcanoes and earthquakes, and explains the '
                                'distribution of continents and oceans. At convergent '
                                'boundaries: continental-continental collisions form '
                                'fold mountains (e.g., the Himalaya); '
                                'oceanic-continental collisions cause the oceanic '
                                'plate to sink, triggering volcanic activity and '
                                'earthquakes. At divergent boundaries, new crust forms '
                                '(e.g., the Mid-Atlantic Ridge). At transform '
                                'boundaries, plates slide past each other, mainly '
                                'causing earthquakes (e.g., the San Andreas Fault).',
                     'keywords': ['beneath',
                                  'broken',
                                  'causes',
                                  'causing',
                                  'crust',
                                  "earth's",
                                  'earthquakes',
                                  'into',
                                  'large',
                                  'layer',
                                  'mantle',
                                  'morgan',
                                  'mountains',
                                  'move',
                                  'outer',
                                  'over',
                                  'plate',
                                  'plates',
                                  'proposed',
                                  'semi-molten',
                                  'several',
                                  'slowly',
                                  'small',
                                  'tectonic',
                                  'tectonics',
                                  'that',
                                  'them',
                                  'theory',
                                  'volcanoes',
                                  'what']},
 'weathering_erosion': {'chapter': "2. Shaping of the Earth's Surface",
                        'aliases': ['weathering',
                                    'erosion',
                                    'gradation',
                                    'agents of gradation'],
                        'definition': 'Weathering is the breakdown of rocks at the '
                                      "Earth's surface; erosion is the wearing away "
                                      'and transport of that broken material by agents '
                                      'like water, wind, ice, and waves.',
                        'short': "Weathering breaks down rocks on the Earth's surface, "
                                 'and erosion carries the broken material away, '
                                 'together reshaping landforms over time.',
                        'medium': 'Weathering and erosion are processes of gradation. '
                                  'Physical, chemical and biological weathering break '
                                  'rocks down where they stand; agents of gradation '
                                  '(rivers, waves and currents, glaciers, wind, and '
                                  'underground water) then erode and transport this '
                                  'material, creating landforms such as river valleys '
                                  'and meanders, beaches, glacial valleys, desert '
                                  'features, and caves.',
                        'long': 'Weathering and erosion are key processes of gradation '
                                "that shape the Earth's surface. Weathering is the "
                                'breakdown of rocks in place, and includes physical, '
                                'chemical and biological weathering. Erosion is the '
                                'removal and transport of the weathered material by '
                                'agents of gradation such as rivers (which create '
                                'meanders, valleys), waves and currents (which shape '
                                'beaches and coastal features), glaciers (which carve '
                                'U-shaped valleys and cirques), wind (which forms '
                                'features like yardangs in dry regions), and '
                                'underground water (which dissolves limestone to form '
                                'caves). These processes affect human occupations '
                                '(farming, tourism, settlement patterns) and can also '
                                'cause hazards such as landslides and Glacial Lake '
                                'Outburst Floods (GLOFs).',
                        'short_note': '• Weathering = breakdown of rock in place — '
                                      'physical (temperature/frost/wind), chemical '
                                      '(reaction with water/air/acid), biological '
                                      '(plant roots, animals, micro-organisms).\n'
                                      '• Erosion = removal + TRANSPORT of weathered '
                                      'material (weathering does not involve movement; '
                                      'erosion does).\n'
                                      '• Agents of gradation: running water, glaciers, '
                                      'wind, waves/currents, groundwater.\n'
                                      '• Landforms shaped human history: river plains '
                                      '(Ganga, Nile, Indus) → early cities; mountains '
                                      '(Himalayas) = barrier + cultural exchange via '
                                      'passes; deserts (Thar) → trade routes; coasts → '
                                      'trade & cultural contact.',
                        'keywords': ['agents',
                                     'away',
                                     'breakdown',
                                     'breaks',
                                     'broken',
                                     'carries',
                                     'down',
                                     "earth's",
                                     'erosion',
                                     'gradation',
                                     'landforms',
                                     'like',
                                     'material',
                                     'over',
                                     'reshaping',
                                     'rocks',
                                     'surface',
                                     'that',
                                     'time',
                                     'together',
                                     'transport',
                                     'water',
                                     'waves',
                                     'wearing',
                                     'weathering',
                                     'wind']},
 'river_landforms': {'chapter': "2. Shaping of the Earth's Surface",
                     'aliases': ['river landforms',
                                 'waterfall',
                                 'meander',
                                 'delta',
                                 'oxbow lake',
                                 'landforms made by rivers'],
                     'definition': "Landforms created by a river's erosion, transport "
                                   'and deposition along its course — waterfalls, '
                                   'meanders, and deltas.',
                     'short': 'Rivers create different landforms along their course: '
                              'waterfalls and V-shaped valleys in the upper course, '
                              'meanders and oxbow lakes in the middle course, and '
                              'deltas in the lower course.',
                     'medium': 'Rivers shape the land via erosion, transportation and '
                               'deposition, producing different landforms in their '
                               'upper course (V-shaped valleys, waterfalls), middle '
                               'course (meanders, oxbow lakes), and lower course '
                               '(deltas) — landforms vital for farming, irrigation, '
                               'navigation and fishing, though deltas can be '
                               'flood-prone.',
                     'long': 'Rivers shape land through erosion, transportation and '
                             'deposition. In the upper course (steep gradient), rivers '
                             'form V-shaped valleys, waterfalls and rapids — a '
                             'waterfall forms where hard rock resists erosion while '
                             'softer rock below wears away, creating a sudden drop. In '
                             'the middle course, the river meanders (winds in bends) '
                             'as it erodes outer banks and deposits sediment on inner '
                             'banks, sometimes cutting off a loop to form an oxbow '
                             'lake; the fertile soil deposited here supports '
                             'agriculture and settlement. In the lower course, the '
                             'river deposits large amounts of sediment at its mouth, '
                             'forming a delta — a fan-shaped, highly fertile area good '
                             'for crops like rice and jute and for fishing, but prone '
                             'to flooding (e.g., the Sundarbans delta).',
                     'short_note': '• Upper course: steep, fast → V-shaped valleys, '
                                   'waterfalls, rapids.\n'
                                   '• Middle course: meanders (erosion on outer bank, '
                                   'deposition on inner bank) → oxbow lakes, '
                                   'floodplains.\n'
                                   '• Lower course: slow, heavy deposition → deltas, '
                                   'levees, alluvial fans.\n'
                                   '• Human uses: fertile soil for farming, '
                                   'irrigation, navigation, fishing, tourism; risk = '
                                   'flooding (e.g. Sundarbans delta).',
                     'keywords': ['along',
                                  'course',
                                  'create',
                                  'created',
                                  'delta',
                                  'deltas',
                                  'deposition',
                                  'different',
                                  'erosion',
                                  'lake',
                                  'lakes',
                                  'landforms',
                                  'lower',
                                  'made',
                                  'meander',
                                  'meanders',
                                  'middle',
                                  'oxbow',
                                  'river',
                                  "river's",
                                  'rivers',
                                  'their',
                                  'transport',
                                  'upper',
                                  'v-shaped',
                                  'valleys',
                                  'waterfall',
                                  'waterfalls']},
 'coastal_glacial_wind_groundwater_landforms': {'chapter': "2. Shaping of the Earth's "
                                                           'Surface',
                                                'aliases': ['coastal landforms',
                                                            'glacial landforms',
                                                            'wind landforms',
                                                            'groundwater landforms',
                                                            'sea cliff',
                                                            'moraine',
                                                            'sand dunes',
                                                            'karst topography',
                                                            'yardang',
                                                            'cirque'],
                                                'definition': 'Landforms shaped '
                                                              'respectively by '
                                                              'waves/currents '
                                                              '(coasts), glaciers, '
                                                              'wind, and underground '
                                                              'water.',
                                                'short': 'Besides rivers, three other '
                                                         'agents shape landforms: '
                                                         'waves/currents create '
                                                         'beaches and sea cliffs; '
                                                         'glaciers carve U-shaped '
                                                         'valleys and cirques; wind '
                                                         'forms dunes and yardangs; '
                                                         'and groundwater dissolves '
                                                         'limestone to form caves and '
                                                         'sinkholes.',
                                                'medium': 'Waves/currents shape '
                                                          'coastal landforms (beaches, '
                                                          'cliffs, caves, arches); '
                                                          'glaciers carve U-shaped '
                                                          'valleys, cirques and '
                                                          'fjords, and deposit '
                                                          'moraines; wind erosion in '
                                                          'dry regions forms yardangs '
                                                          'and dunes; and groundwater '
                                                          'dissolves limestone (Karst '
                                                          'topography) to form caves, '
                                                          'stalactites/stalagmites and '
                                                          'sinkholes — each supports '
                                                          'human activities like '
                                                          'tourism, fresh water '
                                                          'supply, and farming.',
                                                'long': 'Waves and currents erode '
                                                        'coastlines to form beaches, '
                                                        'sand bars, sea cliffs, sea '
                                                        'caves, arches and stacks — '
                                                        'beaches support tourism, '
                                                        'fishing and act as natural '
                                                        'barriers against erosion. '
                                                        'Glaciers carve U-shaped '
                                                        'valleys, cirques (bowl-shaped '
                                                        'hollows), aretes (sharp '
                                                        'ridges) and fjords, and '
                                                        'deposit moraines (lateral, '
                                                        'terminal, medial) — these '
                                                        'support tourism, fresh water '
                                                        'supply, and sometimes fertile '
                                                        'soil. Wind erosion in dry '
                                                        'regions creates yardangs, '
                                                        'ventifacts, deflation '
                                                        'hollows, and dunes (barchan, '
                                                        'longitudinal, star, '
                                                        'parabolic) — important for '
                                                        'desert settlement patterns '
                                                        'and as barriers against '
                                                        'desertification. Underground '
                                                        'water dissolves soluble rock '
                                                        'like limestone (Karst '
                                                        'topography) to form caves, '
                                                        'stalactites/stalagmites, '
                                                        'sinkholes and underground '
                                                        'rivers — sources of fresh '
                                                        'water and tourism.',
                                                'short_note': '• Waves/currents → '
                                                              'beaches, sea cliffs, '
                                                              'caves, arches, stacks.\n'
                                                              '• Glaciers → U-shaped '
                                                              'valleys, cirques, '
                                                              'aretes, fjords, '
                                                              'moraines '
                                                              '(lateral/terminal/medial).\n'
                                                              '• Wind → yardangs, '
                                                              'ventifacts, deflation '
                                                              'hollows, dunes '
                                                              '(barchan, longitudinal, '
                                                              'star, parabolic).\n'
                                                              '• Groundwater (Karst '
                                                              'topography, limestone) '
                                                              '→ caves, '
                                                              'stalactites/stalagmites, '
                                                              'sinkholes, underground '
                                                              'rivers.',
                                                'keywords': ['agents',
                                                             'beaches',
                                                             'besides',
                                                             'carve',
                                                             'caves',
                                                             'cirque',
                                                             'cirques',
                                                             'cliff',
                                                             'cliffs',
                                                             'coastal',
                                                             'coasts',
                                                             'create',
                                                             'dissolves',
                                                             'dunes',
                                                             'form',
                                                             'forms',
                                                             'glacial',
                                                             'glaciers',
                                                             'groundwater',
                                                             'karst',
                                                             'landforms',
                                                             'limestone',
                                                             'moraine',
                                                             'other',
                                                             'respectively',
                                                             'rivers',
                                                             'sand',
                                                             'shape',
                                                             'shaped',
                                                             'sinkholes',
                                                             'three',
                                                             'topography',
                                                             'u-shaped',
                                                             'underground',
                                                             'valleys',
                                                             'water',
                                                             'waves/currents',
                                                             'wind',
                                                             'yardang',
                                                             'yardangs']},
 'landforms_disasters': {'chapter': "2. Shaping of the Earth's Surface",
                         'aliases': ['landslides',
                                     'avalanches',
                                     'glofs',
                                     'dust storms',
                                     'landform disasters',
                                     'glacial lake outburst floods'],
                         'definition': 'Hazards linked to landforms: landslides, '
                                       'avalanches, GLOFs (Glacial Lake Outburst '
                                       'Floods), and dust storms.',
                         'short': 'Landform-related disasters include landslides '
                                  '(unstable slopes), avalanches (unstable snow on '
                                  'slopes), GLOFs (sudden release of glacial lake '
                                  'water), and dust storms (strong winds lifting dry '
                                  'soil).',
                         'medium': 'Four landform-linked disasters combine natural and '
                                   'human causes: landslides (unstable rain-soaked or '
                                   'shaken slopes, worsened by '
                                   'deforestation/construction), avalanches (unstable '
                                   "mountain snowpacks), GLOFs (a glacial lake's "
                                   'ice/moraine dam suddenly bursting), and dust '
                                   'storms (strong winds lifting dry, exposed soil in '
                                   'arid regions).',
                         'long': 'Landslides occur when heavy rainfall, earthquakes, '
                                 'steep slopes and loose rock combine with human '
                                 'causes like deforestation, mining and unplanned '
                                 'hillside construction to destabilise slopes. '
                                 'Avalanches occur when heavy snowfall or a '
                                 'temperature rise makes a mountain snowpack unstable, '
                                 'sometimes triggered by human activity like skiing or '
                                 'construction. GLOFs (Glacial Lake Outburst Floods) '
                                 'happen when rapid glacier melting swells a glacial '
                                 'lake until its ice/moraine dam collapses (sometimes '
                                 'triggered by earthquakes or landslides), releasing a '
                                 'destructive flood downstream. Dust storms arise when '
                                 'strong winds lift loose, dry soil in drought-hit or '
                                 'sparsely vegetated desert/semi-arid regions, '
                                 'worsened by deforestation, overgrazing and climate '
                                 'change.',
                         'short_note': '• Landslide: rainfall/earthquake + steep/loose '
                                       'slope + human causes (deforestation, mining, '
                                       'construction).\n'
                                       '• Avalanche: heavy snowfall/temperature rise '
                                       'on steep slopes; triggers = wind, quakes, '
                                       'human activity.\n'
                                       '• GLOF: glacier melt → swollen glacial lake → '
                                       'ice/moraine dam bursts → sudden downstream '
                                       'flood.\n'
                                       '• Dust storm: strong wind + dry, loose, '
                                       'sparsely-vegetated soil (drought, '
                                       'deforestation, overgrazing).',
                         'keywords': ['avalanches',
                                      'disasters',
                                      'dust',
                                      'floods',
                                      'glacial',
                                      'glofs',
                                      'hazards',
                                      'include',
                                      'lake',
                                      'landform',
                                      'landform-related',
                                      'landforms',
                                      'landslides',
                                      'lifting',
                                      'linked',
                                      'outburst',
                                      'release',
                                      'slopes',
                                      'snow',
                                      'soil',
                                      'storms',
                                      'strong',
                                      'sudden',
                                      'unstable',
                                      'water',
                                      'winds']},
 'atmosphere': {'chapter': '3. Atmosphere and Climate',
                'aliases': ['what is atmosphere',
                            'composition of atmosphere',
                            'layers of atmosphere'],
                'definition': 'The blanket of gases surrounding the Earth, held in '
                              'place by gravity, that supports life and shapes weather '
                              'and climate.',
                'short': 'The atmosphere is the blanket of air surrounding the Earth, '
                         'held by gravity; it is mainly nitrogen (78%) and oxygen '
                         '(21%), with small amounts of carbon dioxide, argon, water '
                         'vapour and dust.',
                'medium': 'The atmosphere is a mixture of gases surrounding the Earth, '
                          'pulled down by gravity. Nitrogen (78%) and oxygen (21%) are '
                          'the most abundant gases, with carbon dioxide (0.04%), argon '
                          '(0.93%) and traces of helium, neon, krypton, xenon, ozone '
                          'and hydrogen making up the rest, along with variable water '
                          'vapour (0.1–0.4%) and dust. The atmosphere shields us from '
                          'harmful solar radiation, regulates temperature by trapping '
                          "some of the Sun's energy, and drives weather and climate.",
                'long': 'The atmosphere has a layered structure based on temperature '
                        'and density changes with altitude:\n'
                        '1. Troposphere (~0–12 km): temperature decreases with '
                        'altitude; contains air we breathe, most water vapour and '
                        'clouds; almost all weather (rain, fog, hail) occurs here. '
                        'Separated from the stratosphere by the tropopause.\n'
                        '2. Stratosphere (~12–50 km): free of clouds, ideal for '
                        'aeroplanes; contains the ozone layer, which filters harmful '
                        'UV radiation. Ends at the stratopause.\n'
                        '3. Mesosphere (~50–80 km): temperature decreases with '
                        'altitude; most meteorites burn up here. Ends at the '
                        'mesopause.\n'
                        '4. Thermosphere (~80–700 km): temperature rises rapidly '
                        '(absorbs X-rays/UV); contains the ionosphere (helps radio '
                        'transmission) and is where auroras occur.\n'
                        '5. Exosphere (uppermost): very thin air; light gases (helium, '
                        'hydrogen) escape into space due to weak gravity.\n'
                        'Note: temperature decreases with altitude ONLY in the '
                        'troposphere and mesosphere.',
                'short_note': '• Gases: N₂ 78%, O₂ 21%, CO₂ 0.04%, Ar 0.93%, others '
                              '0.03% + variable water vapour & dust.\n'
                              '• Layers (low→high): Troposphere → Stratosphere (ozone '
                              'layer) → Mesosphere → Thermosphere (ionosphere, '
                              'auroras) → Exosphere.\n'
                              '• Boundaries: tropopause, stratopause, mesopause.\n'
                              '• Temp decreases with altitude only in troposphere & '
                              'mesosphere; rises rapidly in thermosphere.\n'
                              '• Functions: shields from UV, regulates temperature, '
                              'drives weather.',
                'keywords': ['amounts',
                             'argon',
                             'atmosphere',
                             'blanket',
                             'carbon',
                             'climate',
                             'composition',
                             'dioxide',
                             'dust',
                             'earth',
                             'gases',
                             'gravity',
                             'held',
                             'layers',
                             'life',
                             'mainly',
                             'nitrogen',
                             'oxygen',
                             'place',
                             'shapes',
                             'small',
                             'supports',
                             'surrounding',
                             'that',
                             'vapour',
                             'water',
                             'weather',
                             'what',
                             'with']},
 'weather_vs_climate': {'chapter': '3. Atmosphere and Climate',
                        'aliases': ['weather and climate',
                                    'difference between weather and climate',
                                    'elements of weather'],
                        'definition': 'Weather is the hour-to-hour/day-to-day '
                                      'condition of the atmosphere; climate is the '
                                      'average weather of a place over a long period '
                                      '(usually 30+ years).',
                        'short': "Weather refers to the atmosphere's condition on a "
                                 'given day or hour, while climate is the average '
                                 'weather pattern of a place over a long period, '
                                 'usually 30 years or more.',
                        'medium': 'Weather is short-term and can vary significantly '
                                  'day to day, while climate is the sum total of '
                                  'weather conditions and variations over a large area '
                                  'for an extended period, usually thirty years or '
                                  'more. Both are shaped by the same key elements — '
                                  'temperature, humidity, precipitation, wind, and '
                                  'atmospheric pressure.',
                        'long': 'Weather is short-term and changes from day to day or '
                                'hour to hour (is it raining, is it sunny). Climate is '
                                'the sum total of weather conditions and variations '
                                'over a large area for an extended period (usually '
                                'thirty years or more). Both are shaped by elements '
                                'such as temperature, precipitation, humidity, wind, '
                                'and atmospheric pressure. Temperature is affected '
                                'mainly by insolation (incoming solar energy), which '
                                'decreases from equator to poles. Humidity is the '
                                'presence of water vapour in air. Precipitation (rain, '
                                'snow, sleet, hail) occurs when saturated air releases '
                                'water vapour. Atmospheric pressure is the weight of '
                                "air on the Earth's surface — high pressure (cold, "
                                'sinking air) brings clear skies, low pressure (warm, '
                                'rising air) brings clouds and rain; wind is air '
                                'moving from high to low pressure.',
                        'short_note': '• Weather = short-term, day-to-day; Climate = '
                                      'long-term average (≥30 years).\n'
                                      '• 5 elements: temperature, humidity, '
                                      'precipitation, wind, atmospheric pressure.\n'
                                      '• Temperature ↓ from equator to poles '
                                      '(insolation effect).\n'
                                      '• High pressure → clear/sunny; Low pressure → '
                                      'cloudy/wet.\n'
                                      '• Wind = air moving high-pressure → '
                                      'low-pressure; named by the direction it blows '
                                      'FROM (e.g., westerly).\n'
                                      '• Local winds: sea breeze (sea→land, daytime), '
                                      'land breeze (land→sea, night-time).',
                        'keywords': ['atmosphere',
                                     "atmosphere's",
                                     'average',
                                     'between',
                                     'climate',
                                     'condition',
                                     'difference',
                                     'elements',
                                     'given',
                                     'hour',
                                     'hour-to-hour/day-to-day',
                                     'long',
                                     'more',
                                     'over',
                                     'pattern',
                                     'period',
                                     'place',
                                     'refers',
                                     'usually',
                                     'weather',
                                     'while',
                                     'years']},
 'monsoon': {'chapter': '3. Atmosphere and Climate',
             'aliases': ['monsoon',
                         'indian monsoon',
                         'south west monsoon',
                         'north east monsoon',
                         'seasons in india'],
             'definition': 'The seasonal reversal of wind direction over the Indian '
                           "subcontinent, from the Arabic word mausim ('season').",
             'short': 'Monsoon refers to the seasonal reversal of wind direction over '
                      'India — moist south-west winds bring summer rain, while dry '
                      'north-east winds dominate winter.',
             'medium': "India's climate is strongly shaped by monsoon winds — the term "
                       "comes from the Arabic 'mausim' (season). The south-west "
                       '(summer) monsoon blows from sea to land between June and '
                       'September, caused by the Indian landmass heating faster than '
                       'the ocean, creating low pressure over land and high pressure '
                       'over the (cooler) ocean; moist winds flow from the Arabian Sea '
                       "and Bay of Bengal onto land, bringing most of India's annual "
                       'rainfall. The north-east (winter) monsoon (October to '
                       'February) reverses this — the landmass cools faster than the '
                       'sea, so cold dry winds blow from land to sea, though winds '
                       'crossing the Bay of Bengal pick up moisture and bring rain to '
                       'Tamil Nadu, Andhra Pradesh and parts of Karnataka.',
             'long': 'The Indian Meteorological Department (IMD) recognises four '
                     'seasons: Winter (Dec–early Apr, coldest Dec–Jan), '
                     'Summer/pre-monsoon (Apr–Jun/Jul), Monsoon/rainy (Jun–Sep, '
                     'dominated by the south-west monsoon), and '
                     'Post-monsoon/retreating monsoon (Oct–Dec). Monsoon plays a vital '
                     'role in Indian life: most agriculture depends on it for sowing '
                     'and growing crops, and it affects water supply, transport, '
                     'festivals and employment. Excess rainfall causes floods (e.g., '
                     'the 2025 Punjab floods, caused by heavy monsoon rain plus weak '
                     'river embankments, encroachment near rivers, and silted-up '
                     'dams/rivers); weak monsoons cause droughts.',
             'short_note': "• Monsoon = seasonal reversal of wind (Arabic 'mausim' = "
                           'season).\n'
                           '• SW/summer monsoon (Jun–Sep): sea→land, moist, brings '
                           'most rainfall; caused by land heating faster than sea → '
                           'low pressure over land.\n'
                           '• NE/winter monsoon (Oct–Feb): land→sea, dry, but picks up '
                           'moisture over Bay of Bengal → rain in Tamil Nadu, AP, '
                           'parts of Karnataka.\n'
                           '• 4 IMD seasons: Winter, Summer/pre-monsoon, Monsoon, '
                           'Post-monsoon.\n'
                           '• Case study: Punjab Floods 2025 — natural cause (heavy '
                           'monsoon + western disturbances) + human cause (weak '
                           'embankments/dhūsī bāndh, encroachment, siltation, late '
                           'warnings).',
             'importance': 'Monsoon plays a vital role in the lives of people in '
                           "India. Most of India's agriculture depends on monsoon "
                           'rainfall, as farmers rely on it for sowing and growing '
                           'crops. A good monsoon ensures sufficient food production '
                           'and water supply in rivers, reservoirs and wells, and also '
                           'affects daily life, transport, festivals and employment, '
                           'especially in rural areas. However, excessive rainfall can '
                           'cause floods, while weak monsoons can lead to droughts — '
                           "so monsoon greatly influences India's economy, lifestyle, "
                           'and livelihoods.',
             'causes': 'South-west (summer) monsoon: the Indian landmass heats up '
                       'faster than the surrounding ocean in summer, creating a '
                       'low-pressure area over land and relatively higher pressure '
                       'over the (cooler) ocean; since winds move from high to low '
                       'pressure, moist winds blow from the Arabian Sea and Bay of '
                       'Bengal onto land (June–September). North-east (winter) '
                       'monsoon: the landmass cools faster than the sea in winter, '
                       'reversing the pressure pattern, so cold dry winds blow from '
                       'land to sea (October–February) — except where they cross the '
                       'Bay of Bengal and pick up moisture, bringing rain to Tamil '
                       'Nadu, Andhra Pradesh and parts of Karnataka.',
             'effects': "Positive: monsoon rainfall supports most of India's "
                        'agriculture, refills rivers/reservoirs/groundwater, and '
                        'shapes festivals and rural employment. Negative: excess '
                        'rainfall can cause floods (as in the Punjab Floods of 2025, '
                        'worsened by weak river embankments, encroachment near rivers, '
                        'and siltation), while a weak monsoon can cause drought — both '
                        "disrupt agriculture, the economy, and people's livelihoods.",
             'keywords': ['arabic',
                          'bring',
                          'direction',
                          'dominate',
                          'east',
                          'from',
                          'india',
                          'indian',
                          'mausim',
                          'moist',
                          'monsoon',
                          'north',
                          'north-east',
                          'over',
                          'rain',
                          'refers',
                          'reversal',
                          'season',
                          'seasonal',
                          'seasons',
                          'south',
                          'south-west',
                          'subcontinent',
                          'summer',
                          'west',
                          'while',
                          'wind',
                          'winds',
                          'winter',
                          'word']},
 'human_evolution': {'chapter': '4. Early Humans and Beginning of Civilisation',
                     'aliases': ['biological evolution',
                                 'cultural evolution',
                                 'human ancestors',
                                 'early humans'],
                     'definition': 'Biological evolution = the gradual '
                                   'physical/genetic change in humans over time; '
                                   'cultural evolution = how humans adapted through '
                                   'tools, ideas, and social organisation.',
                     'short': 'Early human history is understood through biological '
                              'evolution (physical/genetic change) and cultural '
                              'evolution (adaptation through tools, skills and social '
                              'organisation), since it mostly predates writing.',
                     'medium': 'The period before writing is studied mainly through '
                               'archaeology since there are no written records. Human '
                               'ancestors first appear in the fossil record in Africa, '
                               'Asia and other regions. Two linked processes explain '
                               'human development: biological evolution (gradual '
                               'physical and genetic change) and cultural evolution '
                               '(how humans adapted to environments through tools, '
                               'fire, language, and social organisation). Over time, '
                               'hunter-gatherers developed better tools (including bow '
                               'and arrow, parallel-sided blades), symbolic '
                               'communication, and decoration, showing increasing '
                               'cultural sophistication.',
                     'long': 'It is generally agreed that our earliest ancestors, the '
                             'australopithecines (australis = southern + pithecus = '
                             'primate), evolved in Africa and gradually developed '
                             'biologically into modern Homo sapiens. Homo erectus, an '
                             'early upright human ancestor who made stone tools (hand '
                             'axes, cleavers), was the first hominin to leave Africa, '
                             'spreading into Asia and Europe roughly 2 million to '
                             '500,000 years ago. Homo sapiens (modern humans) evolved '
                             'in Africa around 300,000 years ago, with a major '
                             'migration out of Africa around 125,000 years ago, '
                             'eventually spreading across the whole Earth. Cultural '
                             'evolution happened alongside this — during the '
                             'Quaternary Period (last 26 lakh years), changing climate '
                             'pushed humans to develop tools, techniques and '
                             'technology. The Neolithic Revolution then marked a '
                             'turning point: domesticating select plants and animals '
                             'let humans shift from hunting-gathering to '
                             'farming/herding and settle in one place. In the Indian '
                             'subcontinent this shows regional variation — by around '
                             '2500 BCE, most of the subcontinent was occupied by '
                             'Neolithic agricultural communities practising cattle, '
                             'sheep and goat herding, laying the basis for the Bronze '
                             'Age and, eventually, the Sindhu–Sarasvatī (Harappan) '
                             'Civilisation.',
                     'short_note': '• Pre-writing history = studied via archaeology '
                                   '(no written records; >99% of human history falls '
                                   'in this period).\n'
                                   '• Biological evolution: australopithecines → Homo '
                                   'erectus (first hominin out of Africa, ~2 '
                                   'mn–500,000 yrs ago; stone tools) → Homo sapiens '
                                   '(evolved in Africa ~300,000 yrs ago; major exit '
                                   '~125,000 yrs ago).\n'
                                   '• Cultural evolution = tools, fire, language, '
                                   'social adaptation during the Quaternary Period '
                                   '(last 26 lakh years).\n'
                                   '• Hunter-gatherers → tool improvements (bow & '
                                   'arrow) → symbolic communication/decoration.\n'
                                   '• Neolithic Revolution = domestication of plants & '
                                   'animals → settled farming.\n'
                                   '• India: by ~2500 BCE, Neolithic farming/herding '
                                   'communities widespread → basis for Bronze Age → '
                                   'Sindhu–Sarasvatī (Harappan) Civilisation.',
                     'keywords': ['adaptation',
                                  'adapted',
                                  'ancestors',
                                  'biological',
                                  'change',
                                  'cultural',
                                  'early',
                                  'evolution',
                                  'gradual',
                                  'history',
                                  'human',
                                  'humans',
                                  'ideas',
                                  'mostly',
                                  'organisation',
                                  'over',
                                  'physical/genetic',
                                  'predates',
                                  'since',
                                  'skills',
                                  'social',
                                  'through',
                                  'time',
                                  'tools',
                                  'understood',
                                  'writing']},
 'stone_age_tools': {'chapter': '4. Early Humans and Beginning of Civilisation',
                     'aliases': ['stone age',
                                 'palaeolithic period',
                                 'mesolithic period',
                                 'neolithic period',
                                 'old stone age',
                                 'new stone age',
                                 'microliths',
                                 'palaeolithic tools',
                                 'attirampakkam',
                                 'bhimbetka'],
                     'definition': "The Stone Age is broadly divided into three "
                                   "stages — Palaeolithic ('old stone'), Mesolithic "
                                   "('middle stone'), and Neolithic ('new stone') — "
                                   'based on the type of stone tools people made and '
                                   'used.',
                     'short': 'The Stone Age had three stages — Palaeolithic (large '
                              'cutting tools like handaxes), Mesolithic (small '
                              'microlithic tools for hunting/fishing), and Neolithic '
                              '(polished tools plus farming) — named from the Greek '
                              "for 'old,' 'middle,' and 'new' stone.",
                     'medium': "The word 'palaeo' means old and 'lithic' means stone, "
                               'so the Palaeolithic (Old Stone Age) is when early '
                               'humans made large cutting tools such as handaxes, '
                               'cleavers, scrapers and choppers from quartzite and '
                               'limestone to chop meat, dig tubers, and scrape animal '
                               'skin. In the Indian subcontinent, the oldest human '
                               'settlement dates back about 2 million years, with '
                               'Attirampakkam (Tamil Nadu) dated to about 1.5–1.7 '
                               'million years ago and Isampur (Karnataka) to about 1.2 '
                               'million years ago. Later Palaeolithic humans invented '
                               'smaller tools (scrapers, borers, points), then the bow '
                               'and arrow and microblades, and began symbolic '
                               'communication and cave/rock-shelter art (as seen at '
                               'Bhimbetka, Madhya Pradesh).',
                     'long': 'The Stone Age is broadly divided into three stages based '
                             'on tool technology: (1) Palaeolithic (Old Stone Age) — '
                             'large stone tools like handaxes and cleavers, plus '
                             'scrapers and choppers, made mainly for chopping meat, '
                             'digging tubers and scraping hides; the oldest Indian '
                             'sites include Attirampakkam (Tamil Nadu, ~1.5–1.7 '
                             'million years ago) and Isampur (Karnataka, ~1.2 million '
                             'years ago). Later Palaeolithic humans made smaller, more '
                             'efficient tools (scrapers, borers, pointed projectiles), '
                             'and eventually the bow and arrow and parallel-sided '
                             'microblade tools; they also developed symbolic '
                             'communication, cave/rock-shelter paintings, body '
                             'pigments, and the first beads of stone, bone and shell — '
                             'these developments are linked to Homo sapiens, who '
                             'spread across the world, including Australia and the '
                             'Americas, between about 50,000 and 12,000 years ago. (2) '
                             'Mesolithic (Middle Stone Age) — around 12,000 years ago '
                             "Earth's climate warmed, forests and grasslands expanded, "
                             'and the resulting population explosion (the first in '
                             'human history) was supported by microlithic (tiny stone) '
                             'tools used for hunting, and for gathering marine/'
                             'freshwater aquatic food; art flourished, and caves/rock '
                             'shelters such as the World Heritage Site of Bhimbetka '
                             '(Madhya Pradesh) show extensive Mesolithic-era rock art. '
                             '(3) Neolithic (New Stone Age) — as hunter-gatherers '
                             'grew familiar with seasons and food resources, they '
                             'gradually shifted to a food-producing way of life, known '
                             'as the Neolithic Revolution: the domestication of select '
                             'plants and animals, development of polished stone tools '
                             'for farming and processing, earthenware pottery, and the '
                             'first permanent village settlements — laying the '
                             'foundation for the later Bronze Age, Chalcolithic and '
                             'Iron Age, and eventually the urban revolution. This '
                             'transition to farming did not happen everywhere at the '
                             'same time; it occurred at different periods in '
                             'different regions of the world.',
                     'short_note': "• Palaeolithic ('old stone'): large tools — "
                                   'handaxes, cleavers, scrapers, choppers (quartzite, '
                                   'limestone). Sites: Attirampakkam (TN, ~1.5–1.7 mn '
                                   'yrs), Isampur (Karnataka, ~1.2 mn yrs).\n'
                                   '• Later Palaeolithic: smaller tools (scrapers, '
                                   'borers, points) → bow & arrow, microblades; cave '
                                   'art, body pigments, first beads.\n'
                                   "• Mesolithic ('middle stone'): warmer climate (from "
                                   '~12,000 yrs ago) → microlithic tools, aquatic '
                                   'food/fishing, first population explosion; '
                                   'Bhimbetka rock art (Madhya Pradesh, World Heritage '
                                   'Site).\n'
                                   "• Neolithic ('new stone') = Neolithic Revolution: "
                                   'domestication of plants/animals, polished tools, '
                                   'pottery, permanent village settlements → basis for '
                                   'Bronze Age & urban revolution.\n'
                                   '• Farming spread at different times in different '
                                   'world regions — not simultaneous everywhere.',
                     'keywords': ['age',
                                  'attirampakkam',
                                  'bhimbetka',
                                  'bow',
                                  'cleavers',
                                  'handaxes',
                                  'isampur',
                                  'lithic',
                                  'mesolithic',
                                  'microlithic',
                                  'microliths',
                                  'neolithic',
                                  'old',
                                  'palaeolithic',
                                  'palaeo',
                                  'pottery',
                                  'revolution',
                                  'scrapers',
                                  'settlements',
                                  'stone',
                                  'tools']},
 'invention_of_writing': {'chapter': '4. Early Humans and Beginning of Civilisation',
                          'aliases': ['invention of writing',
                                      'history vs prehistory',
                                      'harappan script',
                                      'cuneiform',
                                      'hieroglyphics',
                                      'brahmi script'],
                          'definition': "Writing divides history into 'pre-history' "
                                        '(before writing, known only via archaeology) '
                                        "and the 'historical period' (after writing, "
                                        '~5000 years ago onward).',
                          'short': 'The invention of writing, about 5000 years ago, '
                                   'divides the human past into pre-history (known '
                                   'only through archaeological artefacts) and the '
                                   'historical period (also documented in writing).',
                          'medium': 'More than 99% of human history falls in the '
                                    'pre-writing period and is known only from '
                                    'artefacts, with only approximate dating; the last '
                                    '5000 years (the historical period) are documented '
                                    'in writing too, allowing far more accurate dating '
                                    'and detail. Early scripts include the '
                                    'still-undeciphered Harappan script, and the '
                                    'deciphered cuneiform (Sumerian) and hieroglyphic '
                                    '(Egyptian) scripts.',
                          'long': 'More than 99% of human history (from ~3 million to '
                                  '5000 years ago) falls before writing was invented, '
                                  'and is reconstructed mainly from tools and material '
                                  'objects (artefacts); dating from this period is '
                                  'only approximate. The historical period — the last '
                                  '5000 years — is documented through both material '
                                  'remains and written records, which give names, '
                                  'events, and social/political/cultural detail, and '
                                  'allow relatively accurate dating (e.g., dates of '
                                  'coronations, wars). Among the earliest scripts: the '
                                  'Harappan/Sindhu lipi (pictographic, found on seals '
                                  'and pottery) remains undeciphered; the cuneiform '
                                  'script of the Sumerians (Mesopotamia) and the '
                                  'hieroglyphic script of ancient Egypt, which '
                                  'flourished around the same time as the Harappan '
                                  'civilisation, have both been deciphered and mark '
                                  'the beginning of the historical period, about 5000 '
                                  'years ago.',
                          'short_note': '• Pre-writing (>99% of human history): '
                                        'reconstructed only from artefacts; dating '
                                        'approximate.\n'
                                        '• Historical period (last ~5000 years): '
                                        'written + material sources; dating more '
                                        'accurate.\n'
                                        '• Harappan/Sindhu lipi: pictographic, on '
                                        'seals/pottery — still UNDECIPHERED.\n'
                                        '• Cuneiform (Sumerians, Mesopotamia) & '
                                        'hieroglyphics (Egypt): both deciphered; mark '
                                        "start of 'historical period' (~5000 yrs "
                                        'ago).\n'
                                        '• Brahmi script: used in south India & Ganga '
                                        'valley from ~400 BCE; formalised under '
                                        'Emperor Aśhoka (3rd century BCE).',
                          'keywords': ['5000',
                                       'about',
                                       'after',
                                       'also',
                                       'archaeological',
                                       'archaeology',
                                       'artefacts',
                                       'before',
                                       'brahmi',
                                       'cuneiform',
                                       'divides',
                                       'documented',
                                       'harappan',
                                       'hieroglyphics',
                                       'historical',
                                       'history',
                                       'human',
                                       'into',
                                       'invention',
                                       'known',
                                       'only',
                                       'onward',
                                       'past',
                                       'period',
                                       'pre-history',
                                       'prehistory',
                                       'script',
                                       'through',
                                       'writing',
                                       'years',
                                       '~5000']},
 'early_civilisations': {'chapter': '4. Early Humans and Beginning of Civilisation',
                         'aliases': ['mesopotamia',
                                     'egypt civilisation',
                                     'china civilisation',
                                     'harappan civilisation',
                                     'four early civilisations'],
                         'definition': 'Four early world civilisations arose around '
                                       'major rivers: Mesopotamia, Egypt, the '
                                       'Sindhu–Sarasvatī (Harappan), and China.',
                         'short': 'Four early civilisations emerged around river '
                                  'valleys: Mesopotamia (Tigris–Euphrates), Egypt '
                                  '(Nile), Sindhu–Sarasvatī/Harappan (Indus & '
                                  'Ghaggar-Sarasvatī), and China (Huang He).',
                         'medium': 'Four early world civilisations were roughly '
                                   'contemporaneous but developed somewhat '
                                   'independently: Mesopotamia (in modern '
                                   'Iraq/Kuwait), where farming began ~12,000 years '
                                   'ago and the Sumerians built the earliest '
                                   'city-based civilisation, using cuneiform writing '
                                   'and worshipping multiple gods (later dominated by '
                                   'Akkadians, then Assyrians and Babylonians); Egypt, '
                                   'one of the earliest civilisations, known to the '
                                   'Greeks and Romans, which developed along the Nile '
                                   'with a 365-day calendar; the Sindhu–Sarasvatī '
                                   '(Harappan) civilisation in the Indus and '
                                   'Ghaggar-Sarasvatī valleys; and China, which '
                                   'flourished along the Huang He river, adopting '
                                   'copper/bronze metallurgy around 2000 BCE.',
                         'long': 'Mesopotamia and the Harappan civilisation, being '
                                 'geographically closer, show more evidence of '
                                 'interaction/trade with each other than either does '
                                 'with Egypt or China, which developed more '
                                 'independently. Key points per civilisation: '
                                 'Mesopotamia — Sumerians (earliest city-states, '
                                 'cuneiform script), overtaken by Akkadians (~2334 '
                                 'BCE), then Assyrians (north) and Babylonians (south, '
                                 'dominant by ~1400 BCE). Egypt — city-states from '
                                 '~3000 BCE along the Nile, whose annual flooding '
                                 'watered the land; developed a 365-day calendar (12 '
                                 'months × 30 days + 5 extra days). China — flourished '
                                 'along the Huang He, with bronze metallurgy from '
                                 '~2000 BCE.',
                         'short_note': '• 4 early civilisations: Mesopotamia, Egypt, '
                                       'Sindhu–Sarasvatī (Harappan), China — all '
                                       'river-valley based.\n'
                                       '• Mesopotamia: Sumerians (cuneiform) → '
                                       'Akkadians (2334 BCE) → Assyrians/Babylonians.\n'
                                       '• Egypt: Nile floods → agriculture; 365-day '
                                       'calendar; city-states from 3000 BCE.\n'
                                       '• China: Huang He river; bronze metallurgy '
                                       'from ~2000 BCE.\n'
                                       '• Mesopotamia & Harappa show closer '
                                       'geographic/trade links than Egypt/China.',
                         'keywords': ['arose',
                                      'around',
                                      'china',
                                      'civilisation',
                                      'civilisations',
                                      'early',
                                      'egypt',
                                      'emerged',
                                      'four',
                                      'ghaggar-sarasvatī',
                                      'harappan',
                                      'huang',
                                      'indus',
                                      'major',
                                      'mesopotamia',
                                      'nile',
                                      'river',
                                      'rivers',
                                      'sindhu–sarasvatī',
                                      'sindhu–sarasvatī/harappan',
                                      'tigris–euphrates',
                                      'valleys',
                                      'world']},
 'vedic_period': {'chapter': '5. State and Society up to 1000 CE',
                  'aliases': ['vedic period',
                              'four vedas',
                              'vedic political institutions',
                              'vedic assemblies'],
                  'definition': 'The period associated with the composition of the '
                                'four Vedas and the early political/social '
                                'institutions of ancient India.',
                  'short': 'The Vedic Period is associated with the composition of the '
                           'four Vedas and early Indian political institutions, '
                           "including assemblies that advised or checked the ruler's "
                           'power.',
                  'medium': 'The Vedic Period is named for the four Vedas — the '
                            'earliest layer of surviving Indian textual tradition. '
                            'Society during this period had distinct political '
                            'institutions, and historical sources point to assemblies '
                            '(such as Sabhā and Samiti in later scholarship) that '
                            'played a role alongside rulers, reflecting early ideas '
                            'about consultation and collective decision-making. '
                            'Cultural and religious developments during this period '
                            'shaped ideas about duty, ritual, and social order that '
                            'influenced later Indian political thought.',
                  'long': 'The chapter traces political institutions across the Vedic '
                          'Period, including assemblies during Vedic times, and moves '
                          'on to the age of Early Kingdoms and Republics (historical '
                          "sources typically describe 'sixteen' major states/janapadas "
                          'from this era). It also covers the duties and ideals of the '
                          'king, and councils of ministers that advised rulers — '
                          'showing that governance was not purely autocratic but often '
                          'included consultative bodies. Cultural and religious '
                          'developments are traced alongside political changes at each '
                          'stage, reflecting how society, statecraft and belief '
                          'evolved together up to 1000 CE.',
                  'short_note': '• Vedic Period → named after the four Vedas.\n'
                                '• Vedic assemblies existed alongside kingship (early '
                                'consultative institutions).\n'
                                '• Followed by age of Early Kingdoms & Republics — '
                                "sources describe 'sixteen' major janapadas.\n"
                                '• Kings had duties/ideals; council of ministers '
                                'advised rulers.\n'
                                '• Cultural & religious developments tracked through '
                                'each period up to 1000 CE.',
                  'keywords': ['advised',
                               'ancient',
                               'assemblies',
                               'associated',
                               'checked',
                               'composition',
                               'early',
                               'four',
                               'including',
                               'india',
                               'indian',
                               'institutions',
                               'period',
                               'political',
                               'political/social',
                               'power',
                               "ruler's",
                               'that',
                               'vedas',
                               'vedic',
                               'with']},
 'janapadas_mahajanapadas': {'chapter': '5. State and Society up to 1000 CE',
                             'aliases': ['janapada',
                                         'mahajanapada',
                                         'sixteen mahajanapadas',
                                         'magadha',
                                         'early kingdoms and republics'],
                             'definition': 'Janapada = a territorial political unit '
                                           "('where a people first set its feet'); "
                                           'mahājanapada = a larger, more powerful '
                                           'janapada.',
                             'short': 'Janapadas were early territorial '
                                      'kingdoms/republics that replaced purely '
                                      'kinship-based Vedic polities; sixteen larger '
                                      'mahājanapadas later emerged, among which '
                                      'Magadha became the most powerful.',
                             'medium': "The word janapada means 'where a people (jana) "
                                       "first set its feet' — it marks the shift from "
                                       'kinship-based Vedic identity to territorial '
                                       'identity (~1000–600 BCE). As land, farming and '
                                       'trade grew more important, larger units called '
                                       'mahājanapadas emerged (~600 BCE–300 CE); '
                                       'sources describe sixteen of them, and Magadha '
                                       '(in present-day Bihar) rose to be the most '
                                       'powerful.',
                             'long': 'As Vedic society evolved, kin-based political '
                                     'identity (jana, kula) gradually gave way to '
                                     'territorial identity, roughly between 1000 and '
                                     '600 BCE, giving rise to janapadas — the word '
                                     "literally means 'where a people (jana) first set "
                                     "its feet.' As control over land, agriculture and "
                                     'trade routes became more important, some '
                                     'janapadas grew into larger, more complex '
                                     'political units called mahājanapadas (roughly '
                                     '600 BCE–300 CE). Historical sources usually '
                                     'describe sixteen mahājanapadas; among them '
                                     'Magadha (in present-day Bihar) gradually became '
                                     'the most powerful, thanks to its strategic '
                                     'location, fertile plains, and strong rulers — '
                                     'eventually giving rise to the Mauryan Empire '
                                     'under Chandragupta Maurya (foundation dated to '
                                     '321 BCE).',
                             'short_note': "• Janapada = territorial unit ('where a "
                                           "jana first set its feet'); transition from "
                                           'kin-based to territory-based identity, '
                                           '~1000–600 BCE.\n'
                                           '• Mahājanapada = larger political unit '
                                           'than a janapada, ~600 BCE–300 CE; sources '
                                           "describe 'sixteen' mahājanapadas.\n"
                                           '• Magadha (Bihar) → most powerful '
                                           'mahājanapada → basis of the Mauryan Empire '
                                           '(Chandragupta Maurya, 321 BCE).\n'
                                           '• Some early states show evidence that '
                                           'kings could be elected or expelled — royal '
                                           'authority/succession was not always '
                                           'hereditary.',
                             'keywords': ['among',
                                          'became',
                                          'early',
                                          'emerged',
                                          'feet',
                                          'first',
                                          'janapada',
                                          'janapadas',
                                          'kingdoms',
                                          'kingdoms/republics',
                                          'kinship-based',
                                          'larger',
                                          'later',
                                          'magadha',
                                          'mahajanapada',
                                          'mahajanapadas',
                                          'mahājanapada',
                                          'mahājanapadas',
                                          'more',
                                          'most',
                                          'people',
                                          'political',
                                          'polities',
                                          'powerful',
                                          'purely',
                                          'replaced',
                                          'republics',
                                          'sixteen',
                                          'territorial',
                                          'that',
                                          'unit',
                                          'vedic',
                                          'were',
                                          'where',
                                          'which']},
 'mauryan_administration': {'chapter': '5. State and Society up to 1000 CE',
                            'aliases': ['mauryan administration',
                                        'saptanga theory',
                                        'kautilya saptanga',
                                        'seven limbs of state',
                                        'mantri parishad',
                                        'council of ministers'],
                            'definition': "Kauṭilya's Saptāṁga (Seven Limbs) theory "
                                          'describes the state as made up of seven '
                                          'interdependent elements: the king, '
                                          'ministers, territory/population, forts, '
                                          'treasury, army/allies, and law and order.',
                            'short': "Mauryan administration followed Kauṭilya's "
                                     'Saptāṁga theory, viewing the state as seven '
                                     'interlinked parts, with the king advised by a '
                                     'mantri-pariṣhad (council of ministers) rather '
                                     'than ruling entirely alone.',
                            'medium': 'Evidence from the Mauryan period shows that the '
                                      'king did not rule alone but governed through a '
                                      "multi-layered administrative system. Kauṭilya's "
                                      'Saptāṁga (seven limbs) theory names these parts: '
                                      'the king (swāmi), councillors/ministers/high '
                                      'officials (amātya), the territory with its '
                                      'population (janapada), fortified towns and '
                                      'cities (durga), the treasury/wealth of the '
                                      'kingdom (koṣha), the forces of defence and '
                                      'allies (mitra), and law and order (daṇḍa). '
                                      'Central to daily governance was the '
                                      'mantri-pariṣhad (council of ministers), a small '
                                      'body of elder statesmen who advised and '
                                      'supported the king.',
                            'long': "Kauṭilya's Saptāṁga (Seven Limbs) theory of the "
                                    'state, drawn on by the Mauryas, describes the '
                                    'state as seven interdependent elements: (1) '
                                    'swāmi — the king; (2) amātya — the group of '
                                    'councillors, ministers and other high officials; '
                                    '(3) janapada — the territory of the state along '
                                    'with the population inhabiting it; (4) durga — '
                                    'the fortified towns and cities; (5) koṣha — the '
                                    'treasury or wealth of the kingdom; (6) mitra — '
                                    'the forces of defence and the allies; and (7) '
                                    'daṇḍa — law and order. The council of ministers '
                                    '(mantri-pariṣhad) generally included the '
                                    'treasurer, the chief tax collector, the chief '
                                    'legal advisor, and the commander-in-chief of the '
                                    'army. An Aśhokan inscription refers to decisions '
                                    'taken by the council of ministers during the '
                                    "emperor's absence, showing that, in exceptional "
                                    'circumstances, the council could take decisions '
                                    'independently in the public interest — evidence '
                                    'that Mauryan kingship was consultative, not '
                                    'purely autocratic. The Junagadh Rock Inscription '
                                    'near Girnar (Gujarat) records that Puṣhyagupta, a '
                                    'governor appointed by Chandragupta Maurya, '
                                    'constructed a dam on Sudarshana Lake in Saurāṣhṭra '
                                    '(Kathiawad, Gujarat) — showing the active role of '
                                    'the Mauryan state in developing irrigation '
                                    'infrastructure to support agriculture.',
                            'short_note': "• Kauṭilya's Saptāṁga (7 limbs of state): "
                                          'swāmi (king), amātya (ministers/officials), '
                                          'janapada (territory+population), durga '
                                          '(forts/towns), koṣha (treasury), mitra '
                                          '(army/allies), daṇḍa (law & order).\n'
                                          '• Mantri-pariṣhad (council of ministers): '
                                          'treasurer, chief tax collector, chief legal '
                                          'advisor, commander-in-chief — advised the '
                                          'king; NOT a rubber stamp — an Aśhokan '
                                          "inscription shows it could act on its own "
                                          "during the king's absence.\n"
                                          '• Junagadh Rock Inscription (Girnar, '
                                          'Gujarat): records Puṣhyagupta (governor '
                                          'under Chandragupta Maurya) building a dam '
                                          'on Sudarshana Lake → shows Mauryan state '
                                          'role in irrigation.\n'
                                          '• Shows Mauryan kingship was consultative, '
                                          'not purely autocratic.',
                            'keywords': ['administration',
                                         'amatya',
                                         'chandragupta',
                                         'council',
                                         'danda',
                                         'durga',
                                         'kautilya',
                                         'kingdom',
                                         'koshha',
                                         'limbs',
                                         'mantri',
                                         'mauryan',
                                         'ministers',
                                         'mitra',
                                         'parishad',
                                         'saptanga',
                                         'seven',
                                         'state',
                                         'swami',
                                         'theory',
                                         'treasury']},
 'gupta_administration': {'chapter': '5. State and Society up to 1000 CE',
                          'aliases': ['gupta administration',
                                      'gupta empire administration',
                                      'district administration gupta period',
                                      'damodarpur copper plates',
                                      'sandhivigrahika'],
                          'definition': 'The Gupta Empire (320–550 CE) largely '
                                        "retained the Mauryan/Arthaśhāstra-style "
                                        'administrative framework, while adding new '
                                        'offices and expanding provincial and district '
                                        'level government.',
                          'short': 'The Guptas (320–550 CE) largely retained the '
                                   'earlier Mauryan style of administration, with the '
                                   'mantri as head of civil administration, but added '
                                   'new posts like the sāndhivigrahika (minister of '
                                   'peace and war).',
                          'medium': "Interestingly, the Guptas retained much of the "
                                    "earlier form of administration: as in Kauṭilya's "
                                    'Arthaśhāstra, the mantri remained head of civil '
                                    'administration, alongside the commander-in-chief, '
                                    'the general, and the chief of the palace guards. '
                                    'A new post, sāndhivigrahika (minister of peace '
                                    'and war), was introduced during the Gupta '
                                    "period. Kauṭilya's amātyas evolved into a broader "
                                    'category including kumārāmātyas — administrators '
                                    'at the local/provincial level. Administrative '
                                    'units were organised as districts (adhiṣhṭhāna or '
                                    'paṭṭana in the north, nāḍu in the south), groups '
                                    'of villages (vithis in the north; paṭṭalā and '
                                    'kūṛram in the south), and villages as the lowest '
                                    'unit, governed by provincial governors and '
                                    'district officers.',
                            'long': 'Details of Gupta district-level administration '
                                    'are known from inscriptions such as the '
                                    'Damodarpur copper plates from the reign of '
                                    'Kumaragupta I, which record that a district '
                                    'office comprised five members: the head district '
                                    'officer, the chief banker, the chief caravan '
                                    'trader, the chief artisan, and the chief of '
                                    'revenue — showing that local administration '
                                    'included representatives of trade and craft '
                                    'groups, not government officials alone. '
                                    'Administrative divisions were: districts '
                                    '(adhiṣhṭhāna/paṭṭana in the north, nāḍu in the '
                                    'south) → groups of villages, similar to a modern '
                                    'tahsīl (called vithis in the north, paṭṭalā and '
                                    'kūṛram in southern Indian records) → villages, '
                                    'the lowest administrative unit — managed by a '
                                    'large machinery of provincial governors and '
                                    'district officers. At the top, the Gupta system '
                                    'kept the mantri as head of civil administration '
                                    '(as under Kauṭilya) and added the new post of '
                                    'sāndhivigrahika (minister of peace and war); '
                                    "Kauṭilya's amātyas broadened into a category "
                                    'including kumārāmātyas, local/provincial-level '
                                    'administrators. This shows continuity from the '
                                    'Mauryan/Arthaśhāstra model alongside gradual '
                                    'institutional change over centuries.',
                            'short_note': '• Guptas (320–550 CE) retained much of the '
                                          'earlier (Mauryan/Arthaśhāstra) admin '
                                          'structure.\n'
                                          '• Mantri = head of civil administration '
                                          '(continuity); NEW post: sāndhivigrahika '
                                          '(minister of peace & war).\n'
                                          '• Amātya category broadened → included '
                                          'kumārāmātyas (local/provincial '
                                          'administrators).\n'
                                          '• Admin units: district (adhiṣhṭhāna/paṭṭana '
                                          'north, nāḍu south) → village-groups (vithis '
                                          'north; paṭṭalā/kūṛram south) → village '
                                          '(lowest unit).\n'
                                          '• Damodarpur copper plates (Kumaragupta I): '
                                          'district office = 5 members — head district '
                                          'officer, chief banker, chief caravan '
                                          'trader, chief artisan, chief of revenue.',
                            'keywords': ['administration',
                                         'amatya',
                                         'copper',
                                         'damodarpur',
                                         'district',
                                         'gupta',
                                         'guptas',
                                         'kumaragupta',
                                         'kumaramatya',
                                         'mantri',
                                         'nadu',
                                         'plates',
                                         'sandhivigrahika',
                                         'vithis',
                                         'village']},
 'uttaramerur_village_assembly': {'chapter': '5. State and Society up to 1000 CE',
                                  'aliases': ['uttaramerur inscription',
                                              'kudavolai system',
                                              'chola village assembly',
                                              'ballot pot system',
                                              'variyams'],
                                  'definition': 'A 10th-century CE Tamil inscription '
                                                'from Uttaramerur (Chola period) that '
                                                'describes village self-government, '
                                                'including the Kudavolai (ballot pot) '
                                                'system for electing village assembly '
                                                'members.',
                                  'short': 'The Uttaramerur inscription (10th century '
                                           'CE, Chola period, Tamil Nadu) describes a '
                                           'village election system called Kudavolai '
                                           '(ballot pot), an early example of local '
                                           'self-government in India.',
                                  'medium': 'The Uttaramerur inscription of Parantaka '
                                            'I (10th century CE), located in the '
                                            'Vaikuṇṭha Perumāḷ Temple in Kanchipuram '
                                            'district, Tamil Nadu, gives a vivid '
                                            'description of village governance under '
                                            'the Cholas. It describes the Kudavolai '
                                            "('ballot pot') system: names of eligible "
                                            'candidates were written on palm leaves '
                                            'and placed in a large pot, and at a '
                                            'public gathering (often at a temple, for '
                                            'transparency) a young child would draw '
                                            'the leaves one by one to select members '
                                            'for the village assembly and its '
                                            'committees.',
                                  'long': 'The Uttaramerur inscription of the Chola '
                                          'king Parantaka I (10th century CE), found '
                                          'in the Vaikuṇṭha Perumāḷ Temple, '
                                          'Kanchipuram district (Tamil Nadu), is one '
                                          'of the most detailed surviving records of '
                                          'village self-government in early India. It '
                                          'describes the Kudavolai (ballot pot) '
                                          'system used to elect members to the '
                                          'village assembly: names of eligible '
                                          'candidates were written on palm leaves and '
                                          'placed inside a large pot, and during a '
                                          'public gathering a young child was asked '
                                          'to draw the leaves one by one to select '
                                          'representatives — the draw took place in '
                                          'full public view, often at a temple, to '
                                          'ensure fairness. Elected members were then '
                                          'divided into specialised committees '
                                          '(variyams), each responsible for specific '
                                          'duties such as managing irrigation (the '
                                          'tank committee), administering justice, '
                                          'and collecting taxes. The same inscription '
                                          'also specifies eligibility conditions for '
                                          'candidates — for instance, that they '
                                          'should have "honest earnings" and be '
                                          '"pure" of mind — showing that ethical '
                                          'conduct (linked to the wider idea of '
                                          'dharma) was expected of those taking part '
                                          'in public life, not just of kings.',
                                  'short_note': '• Uttaramerur inscription: 10th c. '
                                                'CE, Chola king Parantaka I; Vaikuṇṭha '
                                                'Perumāḷ Temple, Kanchipuram, Tamil '
                                                'Nadu.\n'
                                                "• Kudavolai ('ballot pot') system: "
                                                'candidate names on palm leaves in a '
                                                'pot → child draws leaves in public → '
                                                'elects village assembly members.\n'
                                                '• Elected members divided into '
                                                'variyams (committees) — e.g. tank '
                                                '(irrigation) committee, justice, tax '
                                                'collection.\n'
                                                '• Eligibility: candidates needed '
                                                '"honest earnings" and to be "pure" of '
                                                'mind — links governance to ethical '
                                                'conduct (dharma).\n'
                                                '• Important early evidence of local '
                                                'self-government/election-like '
                                                'practice in Indian history.',
                                  'keywords': ['assembly',
                                               'ballot',
                                               'chola',
                                               'committees',
                                               'election',
                                               'inscription',
                                               'kanchipuram',
                                               'kudavolai',
                                               'parantaka',
                                               'pot',
                                               'self-government',
                                               'tamil',
                                               'uttaramerur',
                                               'variyams',
                                               'village']},
 'dharma_chakravarti': {'chapter': '5. State and Society up to 1000 CE',
                        'aliases': ['dharma',
                                    'chakravarti samrat',
                                    'chakravarti kshetra',
                                    'ashvamedha yajna',
                                    'pan-indian monarch'],
                        'definition': 'Dharma = duty, righteousness and moral conduct '
                                      "(not 'religion'); chakravarti samrāṭ = the "
                                      'ideal of a paramount ruler over the whole '
                                      'Indian subcontinent.',
                        'short': 'Dharma means duty and moral conduct, while '
                                 'chakravarti samrāṭ is the ancient Indian ideal of a '
                                 'supreme ruler whose authority extends over the whole '
                                 'subcontinent.',
                        'medium': "Dharma (from the Sanskrit root dhri, 'to uphold') "
                                  'does not mean religion; it refers to duty, '
                                  'obligation, righteousness and moral conduct — the '
                                  "Mahābhārata says dharma 'is that which upholds "
                                  "beings.' It is closely linked to ideas of justice, "
                                  "and its Buddhist Pāli equivalent is 'dhamma' (as "
                                  "promoted in Aśhoka's edicts). Alongside dharma, "
                                  'early Indian kings expressed a pan-Indian '
                                  'geopolitical vision through concepts like '
                                  "chakravarti samrāṭ (the ideal 'universal paramount "
                                  "ruler'), chakravarti kṣhetra (the 'domain' of such "
                                  'a ruler — defined in the Arthaśhāstra as the region '
                                  'between the Himalayas and the sea), and rituals '
                                  'like the aśhvamedha yajña, showing that political '
                                  'authority was imagined as extending over the whole '
                                  'Indian subcontinent (Jambudvīpa/Bhāratavarṣha), not '
                                  'just one kingdom.',
                        'long': "This ideal recurs across Indian history: Aśhoka's "
                                "edicts speak of his 'energetic exertions' bringing "
                                'spiritual change across Jambudvīpa, and use '
                                "'Prithivi' (equated with chakravarti kṣhetra) for the "
                                'subcontinent, defined in the Arthaśhāstra as "the '
                                'area lying between the Himavat and the sea." In the '
                                'Sangam period, the Chera king Nedunjeral Adan '
                                'claimed the title adhirāja and extended conquests up '
                                'to the Himalayas; in the 11th century CE, Chola '
                                'ruler Rajendra I took the title Gangaikonda to mark '
                                'his conquest of Ganga-basin territory. Meanwhile, '
                                'dharma connected politics with ethics: rulers from '
                                'the Mauryas to the Cholas were expected to govern '
                                "according to dharma — Aśhoka's edicts, for instance, "
                                'promoted dhamma through moral conduct, family '
                                'respect, non-violence and compassion, and the 10th '
                                'century CE Uttaramerur inscription similarly expected '
                                'village-assembly candidates to have "honest '
                                'earnings" and be "pure" of mind — showing that '
                                'Indian statecraft linked political authority to '
                                'ethical responsibility, not power alone.',
                        'short_note': '• Dharma = duty/righteousness/moral conduct '
                                      "(NOT religion); root = Sanskrit 'dhri' ('to "
                                      "uphold'); Buddhist equivalent = 'dhamma'.\n"
                                      '• Chakravarti samrāṭ = ideal of a '
                                      'universal/paramount ruler over the whole '
                                      'subcontinent.\n'
                                      "• Chakravarti kṣhetra = the 'domain' of such a "
                                      "ruler (Arthaśhāstra: 'between the Himavat and "
                                      "the sea').\n"
                                      '• Related terms: Jambudvīpa, Bhāratavarṣha, '
                                      'Prithivi, aśhvamedha & rājasūya yajña.\n'
                                      '• Examples: Aśhoka (edicts on '
                                      'dhamma/Jambudvīpa), Chera king Nedunjeral Adan '
                                      '(title adhirāja), Chola Rajendra I (title '
                                      'Gangaikonda, 11th c. CE).\n'
                                      '• Kingship was NOT always hereditary/absolute — '
                                      'some sources mention elected/expelled kings.',
                        'keywords': ['ancient',
                                     'ashvamedha',
                                     'authority',
                                     'chakravarti',
                                     'conduct',
                                     'dharma',
                                     'duty',
                                     'extends',
                                     'ideal',
                                     'indian',
                                     'kshetra',
                                     'means',
                                     'monarch',
                                     'moral',
                                     'over',
                                     'pan-indian',
                                     'paramount',
                                     'religion',
                                     'righteousness',
                                     'ruler',
                                     'samrat',
                                     'samrāṭ',
                                     'subcontinent',
                                     'supreme',
                                     'while',
                                     'whole',
                                     'whose',
                                     'yajna']},
 'democracy': {'chapter': '6. Democracy',
               'aliases': ['what is democracy',
                           'principles of democracy',
                           'popular sovereignty'],
               'definition': 'A system of government where power ultimately rests with '
                             'the people, exercised through elected representatives '
                             'and protected by rule of law.',
               'short': 'Democracy is a system of government in which power rests with '
                        'the people, who choose representatives through elections and '
                        'hold them accountable.',
               'medium': 'Democracy has roots stretching back to early traditions of '
                         'collective decision-making, and rests on core principles '
                         'including popular sovereignty (ultimate authority lies with '
                         'the people), rule of law (everyone, including the '
                         'government, is bound by law), separation of powers (between '
                         'legislature, executive and judiciary, with checks like '
                         'Question Hour and audits), and a multi-party system that '
                         'lets citizens choose between different political options. '
                         'Democracy also requires safeguarding the rights of '
                         'vulnerable groups and ensuring accountability and '
                         'transparency through mechanisms such as the Comptroller and '
                         'Auditor General, Right to Information, and vigilance '
                         'commissions.',
               'long': 'India, with a population of over 140 crore and a voter base of '
                       "over 96.8 crore (2024), is the world's largest participatory "
                       'democracy, guided by the Constitution of India (adopted 26 Nov '
                       '1949, in force 26 Jan 1950). Five essential principles are: '
                       '(1) Popular sovereignty — ultimate power rests with the '
                       'people, exercised via Universal Adult Franchise (every citizen '
                       '18+ can vote by secret ballot); (2) Rule of Law — everyone is '
                       'equal before the law and no one is above it, backed by the six '
                       'Fundamental Rights (Equality, Freedom, Against Exploitation, '
                       'Freedom of Religion, Cultural & Educational Rights, '
                       'Constitutional Remedies); (3) Separation of Powers — '
                       'legislature (makes laws), executive (implements them) and '
                       'judiciary (interprets them, and can strike down '
                       'unconstitutional laws) check and balance each other, with '
                       'tools like Public Interest Litigation (PIL); (4) '
                       'Accountability & Transparency — enforced through elections, '
                       'public debate, and mechanisms like the Right to Information '
                       '(RTI) Act, 2005; and (5) a Multi-Party System — parties '
                       'representing diverse views compete for votes, and whichever '
                       'wins a majority (or forms a coalition with over 50% seats) '
                       'governs, while others form the opposition, all under the '
                       'Representation of the People Act, 1951. Democracy also '
                       'requires safeguarding the rights of vulnerable groups '
                       'regardless of caste, gender, religion or region.',
               'short_note': '• 5 core principles: Popular Sovereignty (Universal '
                             'Adult Franchise, 18+, secret ballot), Rule of Law (6 '
                             'Fundamental Rights: Equality, Freedom, Against '
                             'Exploitation, Freedom of Religion, Cultural/Educational '
                             'Rights, Constitutional Remedies), Separation of Powers '
                             '(legislature/executive/judiciary + PILs), Accountability '
                             '& Transparency (elections, RTI Act 2005), Multi-Party '
                             'System (RPA 1951; >50% seats → forms govt).\n'
                             '• India: pop. 140+ crore; voters 96.8+ crore (2024); '
                             'Constitution adopted 26 Nov 1949, in force 26 Jan 1950; '
                             'amendable under Art. 368.\n'
                             '• Democracy must also protect vulnerable groups '
                             'regardless of caste/gender/religion/region.',
               'importance': 'Democracy matters because it places the ultimate source '
                             'of power with the people rather than a ruler or a small '
                             'group. Through Universal Adult Franchise, every citizen '
                             'aged 18 and above can vote to choose and change their '
                             'government, which keeps power accountable to the public. '
                             'Democracy also protects citizens through Fundamental '
                             'Rights, the rule of law, and an independent judiciary, '
                             'and it safeguards the rights of vulnerable groups '
                             'regardless of caste, gender, religion or region.',
               'features': ['Popular Sovereignty — power rests with the people '
                            '(Universal Adult Franchise, 18+, secret ballot)',
                            'Rule of Law — equality before law; 6 Fundamental Rights',
                            'Separation of Powers — legislature, executive, judiciary '
                            'check each other (e.g., Public Interest Litigation)',
                            'Accountability & Transparency — elections, public debate, '
                            'RTI Act 2005',
                            'Multi-Party System — parties compete; majority (or '
                            'coalition, >50% seats) forms the government under the '
                            'RPA, 1951'],
               'keywords': ['accountable',
                            'choose',
                            'democracy',
                            'elected',
                            'elections',
                            'exercised',
                            'government',
                            'hold',
                            'people',
                            'popular',
                            'power',
                            'principles',
                            'protected',
                            'representatives',
                            'rests',
                            'rule',
                            'sovereignty',
                            'system',
                            'them',
                            'through',
                            'ultimately',
                            'what',
                            'where',
                            'which',
                            'with']},
 'types_of_democracy': {'chapter': '6. Democracy',
                        'aliases': ['direct democracy',
                                    'representative democracy',
                                    'indirect democracy',
                                    'parliamentary democracy',
                                    'presidential democracy',
                                    'types of democracy'],
                        'definition': 'Democracies can be classified as Direct '
                                      '(citizens decide directly) or Representative '
                                      '(citizens elect representatives), and '
                                      'representative democracies further as '
                                      'Parliamentary or Presidential, based on how the '
                                      'executive relates to the legislature.',
                        'short': 'Democracy can be Direct (citizens participate '
                                 'directly, e.g. Switzerland) or Representative '
                                 '(citizens elect representatives, e.g. India); '
                                 'representative democracies can further be '
                                 'Parliamentary (e.g. India, Canada) or Presidential '
                                 '(e.g. USA).',
                        'medium': 'In a Direct Democracy, citizens directly '
                                  'participate in most decision-making processes; it '
                                  'is difficult to follow in large countries, so it '
                                  'is mainly seen in smaller nations like '
                                  'Switzerland. In a Representative (or Indirect) '
                                  'Democracy — used in India — people elect '
                                  'representatives through periodic elections rather '
                                  'than directly governing themselves, and the '
                                  'government remains accountable to the people. '
                                  'Representative democracies are further of two '
                                  'kinds: Parliamentary Democracy (e.g. India, '
                                  'Canada), where members of the executive are also '
                                  'part of the legislature and the executive is '
                                  'accountable to the legislature, and people elect '
                                  'the legislature but not the executive directly; '
                                  'and Presidential Democracy (e.g. USA), where the '
                                  'executive is independent of the legislature, and '
                                  'the President — elected by the people and '
                                  'accountable to them — heads the executive.',
                        'long': 'Democracies differ in HOW citizens exercise power. '
                                'Direct Democracy: citizens directly participate in '
                                'most decision-making processes (some features of '
                                'representative democracy may still exist); this is '
                                'difficult to follow in large countries because of '
                                'scale, so it is typically associated with smaller '
                                'nations such as Switzerland, where citizens vote '
                                'directly on many issues. Representative (Indirect) '
                                'Democracy: people elect representatives who govern '
                                'on their behalf rather than the people governing '
                                'directly; periodic elections keep the government '
                                'accountable to the people — India follows this '
                                'model. Within representative democracies there are '
                                'two common systems: (1) Parliamentary Democracy '
                                '(India, Canada) — the executive (Prime Minister and '
                                'Council of Ministers) is drawn from and is also part '
                                'of the legislature, and is accountable to the '
                                'legislature; citizens elect the legislature but do '
                                'not directly elect the executive. (2) Presidential '
                                'Democracy (USA) — the executive (the President) is '
                                'independent of the legislature; the President is '
                                'directly elected by the people and is accountable to '
                                'the people rather than to the legislature. '
                                'Democracies across the world follow different '
                                'systems in this way, but they share common '
                                'democratic values and principles such as popular '
                                'sovereignty, rule of law and accountability.',
                        'short_note': '• Direct Democracy: citizens directly '
                                      'participate in decisions; hard in large '
                                      'countries; e.g. Switzerland.\n'
                                      '• Representative/Indirect Democracy: people '
                                      'elect representatives; periodic elections; '
                                      'govt accountable to people; e.g. India.\n'
                                      '• Parliamentary Democracy: executive is part '
                                      'of & accountable to the legislature; people '
                                      'elect legislature, not executive directly; '
                                      'e.g. India, Canada.\n'
                                      '• Presidential Democracy: executive '
                                      '(President) independent of legislature; '
                                      'President directly elected by & accountable '
                                      'to the people; e.g. USA.\n'
                                      '• All types share common democratic values: '
                                      'popular sovereignty, rule of law, '
                                      'accountability.',
                        'features': ['Direct Democracy — citizens directly '
                                     'participate in most decisions (e.g. '
                                     'Switzerland)',
                                     'Representative/Indirect Democracy — citizens '
                                     'elect representatives; periodic elections; '
                                     'govt accountable to people (e.g. India)',
                                     'Parliamentary Democracy — executive is part of '
                                     'and accountable to the legislature (e.g. India, '
                                     'Canada)',
                                     'Presidential Democracy — executive is '
                                     'independent of the legislature; President '
                                     'directly elected (e.g. USA)'],
                        'keywords': ['accountable',
                                     'canada',
                                     'democracy',
                                     'direct',
                                     'elect',
                                     'executive',
                                     'india',
                                     'indirect',
                                     'legislature',
                                     'parliamentary',
                                     'people',
                                     'president',
                                     'presidential',
                                     'representative',
                                     'switzerland',
                                     'types',
                                     'usa']},
 'challenges_to_indian_democracy': {'chapter': '6. Democracy',
                                    'aliases': ['challenges to democracy',
                                                'challenges faced by indian democracy',
                                                'the emergency 1975',
                                                'fake news and democracy',
                                                'threats to democracy'],
                                    'definition': 'Ongoing difficulties that test '
                                                  "India's democracy, including "
                                                  'illiteracy, misinformation, '
                                                  'inequality, and historical episodes '
                                                  'such as the National Emergency of '
                                                  '1975–77.',
                                    'short': 'Indian democracy faces challenges such '
                                             'as illiteracy, misinformation/fake '
                                             'news, inequality and regionalism, and '
                                             'has been tested historically, most '
                                             'notably by the National Emergency of '
                                             '1975–77.',
                                    'medium': 'Democracy requires constant care, '
                                              'awareness, and active participation '
                                              'from both institutions and citizens — '
                                              'it is not limited to elections but is '
                                              'reflected in everyday behaviour and '
                                              'civic responsibility. Despite '
                                              'significant progress in representation '
                                              'and participation, India continues to '
                                              'face challenges such as illiteracy, '
                                              'misinformation, and inequality; the '
                                              'spread of fake news through social '
                                              'media is a growing concern, and '
                                              'poverty, regionalism, gender '
                                              'inequality, and social discrimination '
                                              'create barriers to equal '
                                              'participation. Historically, the '
                                              'National Emergency of 1975–77 (imposed '
                                              'under Articles 352, 356 and 360) was '
                                              'one of the most serious challenges to '
                                              'Indian democracy.',
                                    'long': 'Democracy is not limited to elections — '
                                            'it is reflected in everyday behaviour, '
                                            'decision-making, and civic '
                                            'responsibility, and actions such as '
                                            'damaging public property, spreading '
                                            'misinformation, or violating public '
                                            'rules weaken democratic values, as does '
                                            'public indifference to issues. While '
                                            'India has made significant progress in '
                                            'representation and participation, it '
                                            'continues to face challenges: '
                                            'illiteracy, misinformation and '
                                            'inequality; the spread of fake news, '
                                            'especially via social media, which can '
                                            'influence public opinion, create '
                                            'confusion and even lead to conflict; and '
                                            'poverty, regionalism, gender inequality '
                                            'and social discrimination, which create '
                                            'barriers to equal participation, along '
                                            'with gaps in the effective '
                                            'implementation of laws and policies that '
                                            'can reduce public trust in institutions. '
                                            'The most serious historical challenge '
                                            'came with the Emergency: in the early '
                                            '1970s, public dissatisfaction with the '
                                            'government led by Indira Gandhi grew '
                                            'amid rising unemployment, inflation and '
                                            'allegations of misgovernance, leading to '
                                            'widespread protests. In June 1975, a '
                                            'National Emergency was imposed on '
                                            'grounds of internal disturbance (dealt '
                                            'with under Articles 352, 356 and 360 of '
                                            'the Constitution, covering National '
                                            "Emergency, President's Rule, and "
                                            'Financial Emergency respectively); a '
                                            'majority of Fundamental Rights were '
                                            'suspended, the press was censored, and '
                                            'many political leaders and activists '
                                            'were arrested. Mass movements led by '
                                            'Jayaprakash Narayan (Lok Nayak) '
                                            'mobilised students and citizens, '
                                            'especially in Bihar and Gujarat. The '
                                            'Emergency was lifted in 1977; general '
                                            'elections were held and the ruling '
                                            'government was defeated, demonstrating '
                                            'the strength of Indian democracy and the '
                                            'importance of constitutional safeguards, '
                                            'civil liberties and active citizen '
                                            'participation — highlighting both the '
                                            'vulnerabilities and the resilience of '
                                            'democratic institutions in India.',
                                    'short_note': '• Democracy ≠ only elections — '
                                                  'also everyday civic behaviour '
                                                  '(damaging public property, '
                                                  'misinformation, rule violation all '
                                                  'weaken it).\n'
                                                  '• Ongoing challenges: illiteracy, '
                                                  'misinformation/fake news '
                                                  '(esp. social media), inequality, '
                                                  'poverty, regionalism, gender '
                                                  'inequality, social '
                                                  'discrimination, weak law '
                                                  'implementation.\n'
                                                  '• Emergency (1975–77): imposed '
                                                  'June 1975 under Articles 352 '
                                                  "(National Emergency), 356 "
                                                  "(President's Rule), 360 "
                                                  '(Financial Emergency); causes = '
                                                  'unemployment, inflation, '
                                                  'misgovernance allegations, '
                                                  'protests.\n'
                                                  '• During Emergency: Fundamental '
                                                  'Rights suspended, press censored, '
                                                  'leaders/activists arrested.\n'
                                                  '• Led by/mobilised by: '
                                                  'Jayaprakash Narayan (Lok Nayak) — '
                                                  'esp. Bihar & Gujarat.\n'
                                                  '• Lifted 1977 → elections → ruling '
                                                  'govt defeated → shows democratic '
                                                  'resilience + importance of '
                                                  'constitutional safeguards.',
                                    'causes': 'Structural/social challenges: '
                                              'illiteracy, poverty, regionalism, '
                                              'gender inequality, social '
                                              'discrimination, and gaps in '
                                              'implementing laws/policies. '
                                              'Informational challenge: spread of '
                                              'misinformation and fake news via '
                                              'social media and digital platforms. '
                                              'Historical case (the Emergency, '
                                              '1975–77): caused by growing public '
                                              'dissatisfaction with the government '
                                              'led by Indira Gandhi amid rising '
                                              'unemployment, inflation, and '
                                              'allegations of misgovernance, leading '
                                              'to widespread protests and the '
                                              'declaration of a National Emergency on '
                                              'grounds of internal disturbance.',
                                    'effects': 'Misinformation/fake news can '
                                               'influence public opinion, create '
                                               'confusion, and sometimes lead to '
                                               'conflict; poverty, regionalism, '
                                               'gender inequality and discrimination '
                                               'create unequal participation; weak '
                                               'implementation of laws reduces public '
                                               'trust. The Emergency (1975–77) '
                                               'resulted in suspension of most '
                                               'Fundamental Rights, press censorship, '
                                               'and arrests of political leaders and '
                                               'activists — but its lifting in 1977 '
                                               'and the subsequent electoral defeat '
                                               'of the ruling government showed that '
                                               'Indian democratic institutions could '
                                               'recover and that citizen '
                                               'participation could restore '
                                               'democratic norms.',
                                    'keywords': ['1975',
                                                 '1977',
                                                 'challenges',
                                                 'democracy',
                                                 'emergency',
                                                 'fake',
                                                 'gandhi',
                                                 'illiteracy',
                                                 'indira',
                                                 'inequality',
                                                 'jayaprakash',
                                                 'misinformation',
                                                 'narayan',
                                                 'news',
                                                 'rights',
                                                 'suspended']},
 'democratic_traditions_india': {'chapter': '6. Democracy',
                                 'aliases': ['democratic traditions in india',
                                             'sabha samiti',
                                             'vidhata',
                                             'bauddha sangha',
                                             'constituent assembly'],
                                 'definition': 'Evidence of consultative, collective '
                                               'decision-making runs through Indian '
                                               'history — from Vedic assemblies to the '
                                               'Buddhist Saṁgha to the modern '
                                               'Constituent Assembly.',
                                 'short': "India's democratic ethos has deep "
                                          'historical roots: Vedic assemblies (Sabhā, '
                                          "Samiti, Vidhata), the Buddhist Saṁgha's "
                                          'practice of debate and voting, and finally '
                                          'the Constituent Assembly that drafted '
                                          "independent India's Constitution.",
                                 'medium': "India's democratic ethos evolved over a "
                                           'long history rather than starting in 1947: '
                                           'Vedic assemblies (Sabhā, Samiti, Vidhata) '
                                           'and early republics (gaṇas/saṁghas) '
                                           'practised collective decision-making, the '
                                           'Buddhist Saṁgha chose leaders and decided '
                                           'matters by debate and voting, and — after '
                                           'colonial rule disrupted participation — '
                                           'the freedom struggle revived these ideas, '
                                           'culminating in the Constituent Assembly '
                                           "that drafted India's Constitution.",
                                 'long': 'Democratic ideas in India did not emerge '
                                         'suddenly with independence — they evolved '
                                         'over a long history. In the Vedic period, '
                                         'assemblies such as Sabhā, Samiti and Vidhata '
                                         'practised collective decision-making, and '
                                         'kings ruled in consultation with these '
                                         'assemblies and ministers rather than as '
                                         'sole, independent rulers (a Ṛigveda verse, '
                                         'part of the Aikyamatya Sūktam, celebrates '
                                         'shared counsel and common purpose). Early '
                                         'republican states (gaṇas or saṁghas) also '
                                         'functioned this way. The Bauddha Saṁgha, the '
                                         'monastic community founded by the Buddha, '
                                         'likewise encouraged debate and let members '
                                         'choose leaders and decide matters by voting. '
                                         'Later, the Uttaramerur inscription (10th '
                                         'century CE, Chola period, Tamil Nadu) '
                                         'records the Kudavolai (ballot-pot) system '
                                         'for electing village-assembly members, '
                                         'another important example of a functioning, '
                                         'election-like local institution long before '
                                         'modern democracy. Centuries later, colonial '
                                         'rule disrupted political participation, but '
                                         'the freedom struggle revived democratic '
                                         'ideas, culminating in the Constituent '
                                         'Assembly (formed 1946), which took 2 years, '
                                         '11 months and 18 days to draft the world\'s '
                                         'longest written Constitution — shaped both '
                                         'by these indigenous traditions and by '
                                         'globally-shared democratic values, and '
                                         'chaired in drafting by Dr B.R. Ambedkar.',
                                 'short_note': '• Vedic assemblies: Sabhā, Samiti, '
                                               'Vidhata — consultative bodies '
                                               'alongside kings.\n'
                                               "• Ṛigveda's Aikyamatya Sūktam — verse "
                                               'celebrating shared counsel/common '
                                               'purpose.\n'
                                               '• Early republics: gaṇas/saṁghas — '
                                               'collective governance.\n'
                                               '• Bauddha Saṁgha (Buddhist monastic '
                                               'order): debate + voting to choose '
                                               'leaders/decisions.\n'
                                               '• Uttaramerur inscription (10th c. CE, '
                                               'Chola): Kudavolai ballot-pot system '
                                               'for village-assembly elections.\n'
                                               '• Constituent Assembly: formed 1946; '
                                               'took 2 yrs 11 months 18 days; drafted '
                                               "world's longest written Constitution; "
                                               'Dr B.R. Ambedkar = Chairman, Drafting '
                                               'Committee.',
                                 'keywords': ['assemblies',
                                              'assembly',
                                              'bauddha',
                                              'buddhist',
                                              'collective',
                                              'constituent',
                                              'constitution',
                                              'consultative',
                                              'debate',
                                              'decision-making',
                                              'deep',
                                              'democratic',
                                              'drafted',
                                              'ethos',
                                              'evidence',
                                              'finally',
                                              'from',
                                              'historical',
                                              'history',
                                              'independent',
                                              'india',
                                              "india's",
                                              'indian',
                                              'modern',
                                              'practice',
                                              'roots',
                                              'runs',
                                              'sabha',
                                              'sabhā',
                                              'samiti',
                                              'sangha',
                                              'saṁgha',
                                              "saṁgha's",
                                              'that',
                                              'through',
                                              'traditions',
                                              'vedic',
                                              'vidhata',
                                              'voting']},
 'media_role_democracy': {'chapter': '6. Democracy',
                          'aliases': ['fourth pillar of democracy',
                                      'role of media in democracy',
                                      'media and democracy'],
                          'definition': "The media is often called the 'fourth "
                                        "pillar of democracy' because it voices "
                                        'public concerns and helps hold institutions '
                                        'accountable.',
                          'short': "Media is often called the 'fourth pillar of "
                                   "democracy' because newspapers, news channels and "
                                   'social media raise public issues and help '
                                   'resolve them through appropriate mechanisms.',
                          'medium': 'Alongside the legislature, executive and '
                                    'judiciary, the media plays a critical role in '
                                    'safeguarding people\'s voices and upholding '
                                    'democratic principles — newspapers, news '
                                    'channels and social media platforms raise '
                                    'issues concerning the public and contribute to '
                                    'their resolution through appropriate '
                                    'mechanisms. For this reason, the media is often '
                                    "referred to as the 'fourth pillar of "
                                    "democracy.'",
                          'long': 'In a democracy, the media serves as a voice of '
                                  'the masses. Newspapers, news channels, and social '
                                  'media platforms raise issues concerning the '
                                  'public and contribute to their resolution through '
                                  'appropriate mechanisms — for example, by exposing '
                                  'corruption, reporting on government performance, '
                                  'or amplifying the concerns of ordinary citizens so '
                                  'that institutions are compelled to respond. '
                                  'Because of this critical role in safeguarding '
                                  "people's voices and upholding democratic "
                                  "principles, the media is often called the 'fourth "
                                  "pillar of democracy,' alongside the legislature, "
                                  'executive and judiciary. At the same time, being '
                                  'well-informed is one of the vital responsibilities '
                                  'of a young citizen — reading newspapers, watching '
                                  'news programmes, and using the internet '
                                  'responsibly help people stay aware of national '
                                  'and international events, form informed opinions '
                                  'on public issues, and understand how democracy '
                                  'operates in practice.',
                          'short_note': "• Media = 'fourth pillar of democracy' "
                                        '(alongside legislature, executive, '
                                        'judiciary).\n'
                                        '• Role: voices public concerns, raises '
                                        'issues, helps ensure institutional '
                                        'accountability.\n'
                                        '• Citizen duty: stay informed (newspapers, '
                                        'news programmes, responsible internet use) '
                                        'to form opinions & understand democracy in '
                                        'practice.\n'
                                        '• Caution: social media can also spread '
                                        'misinformation/fake news — a challenge to '
                                        'democracy (see Challenges to Indian '
                                        'Democracy).',
                          'keywords': ['accountability',
                                       'democracy',
                                       'fourth',
                                       'issues',
                                       'masses',
                                       'media',
                                       'news',
                                       'newspapers',
                                       'pillar',
                                       'public',
                                       'voice'],
                          },
 'elections': {'chapter': '7. Elections',
               'aliases': ['what are elections',
                           'why are elections important',
                           'direct and indirect elections'],
               'definition': 'The process through which citizens exercise their right '
                             'to vote to choose representatives, held directly or '
                             'indirectly.',
               'short': 'Elections are the process by which citizens choose their '
                        'representatives, held regularly and periodically to keep '
                        'government accountable to the people.',
               'medium': 'Elections are one of the most important processes for '
                         'exercising democratic rights; regular, periodic elections '
                         'lie at the core of democracy. In India, direct elections '
                         'choose members of the Lok Sabha, Vidhan Sabha, and local '
                         'bodies (Panchayats, municipal corporations) every five '
                         'years, while indirect elections choose the President, Vice '
                         'President, and members of the Rajya Sabha. Elections matter '
                         'because they give citizens the right to choose and hold '
                         'accountable those who make decisions on their behalf — '
                         'captured in the 5 pillars: Representation, Equality, '
                         'Accountability, and Legitimacy (with a 5th slot for students '
                         "to identify) shown in the textbook's diagram.",
               'long': 'The Electoral System: India uses the First-Past-The-Post '
                       '(FPTP) system for Lok Sabha & Vidhan Sabha elections, and '
                       'Proportional Representation (via single transferable vote) for '
                       'Rajya Sabha, Vidhan Parishad, President and Vice President '
                       'elections. Key Laws: the Representation of the People Act, '
                       '1950 (seat allocation, delimitation, electoral rolls, voting '
                       'rights for 18+ citizens) and 1951 (nomination, campaigns, '
                       'voting procedures, disputes, and electoral offences like '
                       'bribery, appeals on religion/caste/race/community/language, or '
                       'taking government-personnel assistance). The Delimitation '
                       'Commission (est. under Article 82; Commissions held in 1952, '
                       '1963, 1973, 2002) fixes constituency boundaries so seats are '
                       'roughly proportional to population. The Election Commission of '
                       'India (ECI), an autonomous constitutional body since 25 '
                       'January 1950 (Articles 324–329), creates/updates electoral '
                       'rolls (including Special Intensive Revision or SIR), decides '
                       'election schedules, registers political parties '
                       '(national/state/registered-unrecognised, with specific '
                       'vote/seat thresholds) and allots symbols, and works to ensure '
                       'free, fair and inclusive elections — e.g., ETPBS for service '
                       'voters, Voter Helpline & Saksham apps for PwDs, cVIGIL for '
                       'reporting Model Code of Conduct violations, and home voting '
                       'for senior citizens (85+) and PwDs (introduced in the 2024 '
                       'General Elections). Political parties organise public opinion, '
                       'campaign on issues, offer voters meaningful choices, and (once '
                       'elected) either form the government or serve as opposition '
                       'ensuring accountability; the Anti-Defection Law (52nd '
                       'Constitutional Amendment, 1985) restricts elected members from '
                       'switching parties. Despite these safeguards, challenges to '
                       'free and fair elections include misinformation, fake news, and '
                       'intimidation.',
               'short_note': '• Direct elections: Lok Sabha, Vidhan Sabha, local '
                             'bodies (every 5 yrs). Indirect: President, VP, Rajya '
                             'Sabha.\n'
                             '• Electoral systems: FPTP (Lok Sabha/Vidhan Sabha) vs '
                             'Proportional Representation/STV (Rajya Sabha, Vidhan '
                             'Parishad, President, VP).\n'
                             '• Key laws: RPA 1950 (rolls, delimitation, voting '
                             'rights) & RPA 1951 (conduct of polls, offences, '
                             'disputes).\n'
                             '• Delimitation Commission: Art. 82; Commissions — 1952, '
                             '1963, 1973, 2002.\n'
                             '• ECI: autonomous, est. 25 Jan 1950, Arts. 324–329; '
                             'functions — electoral rolls/SIR, schedule, party '
                             'registration/symbols, ensuring free & fair polls.\n'
                             '• Party recognition: National / State / '
                             'Registered-Unrecognised (RUPP) — based on vote %/seats '
                             'won.\n'
                             '• Inclusion tools: ETPBS, Voter Helpline, Saksham, '
                             'cVIGIL, home voting (85+/PwD, since 2024 General '
                             'Elections).\n'
                             '• Anti-Defection Law: 52nd Amendment, 1985.\n'
                             '• Challenges: misinformation, fake news, intimidation.',
               'importance': 'Elections matter because regular, periodic elections let '
                             'citizens exercise their right to vote and hold elected '
                             'representatives accountable — this is one of the most '
                             'crucial elements of democracy. Without periodic '
                             'elections, a representative (or a government) could stay '
                             "in power indefinitely without seeking the people's "
                             'mandate again, and citizens could not exercise real '
                             'choice. The textbook links elections to five ideas: '
                             'Representation, Equality, Accountability, and Legitimacy '
                             '(with a fifth left for students to identify) — together '
                             'these are why elections are central to democratic '
                             'functioning.',
               'features': ['Direct elections: Lok Sabha, Vidhan Sabha, local bodies '
                            '(every 5 years)',
                            'Indirect elections: President, Vice President, Rajya '
                            'Sabha',
                            'Electoral systems: FPTP (Lok Sabha/Vidhan Sabha) and '
                            'Proportional Representation/single transferable vote '
                            '(Rajya Sabha, Vidhan Parishad, President, VP)',
                            'Governed by RPA 1950 (rolls, delimitation) and RPA 1951 '
                            '(conduct, offences, disputes)',
                            'Conducted by the autonomous Election Commission of India '
                            '(ECI)'],
               'keywords': ['accountable',
                            'choose',
                            'citizens',
                            'direct',
                            'directly',
                            'elections',
                            'exercise',
                            'government',
                            'held',
                            'important',
                            'indirect',
                            'indirectly',
                            'keep',
                            'people',
                            'periodically',
                            'process',
                            'regularly',
                            'representatives',
                            'right',
                            'their',
                            'through',
                            'vote',
                            'what',
                            'which']},
 'eci_functions': {'chapter': '7. Elections',
                   'aliases': ['election commission of india',
                               'eci',
                               'functions of eci'],
                   'definition': 'The autonomous constitutional body (est. 25 Jan '
                                 '1950) responsible for superintendence, direction and '
                                 'control of elections in India.',
                   'short': 'The Election Commission of India (ECI) is the autonomous '
                            'constitutional body that conducts and oversees elections '
                            'to the Lok Sabha, Rajya Sabha, Vidhan Sabha, Vidhan '
                            'Parishad, President and Vice President.',
                   'medium': 'The ECI, established on 25 January 1950 under Articles '
                             '324–329 of the Constitution, has superintendence, '
                             'direction and control over the entire election process. '
                             'At the state level it works through the Chief Electoral '
                             'Officer and officers like District Election Officers, '
                             'Returning Officers and Electoral Registration Officers.',
                   'long': 'Key ECI functions: (1) Creating and maintaining the '
                           'electoral roll — sending enumerators to households, '
                           'running Special Intensive Revision (SIR) to add eligible '
                           'new voters (esp. those who just turned 18) and delete '
                           'ineligible ones (death, relocation, duplicate entries, '
                           'untraceable persons); (2) Deciding the election schedule, '
                           'considering weather, agricultural cycles, exams and '
                           'festivals; (3) Registering political parties and '
                           'allocating symbols, classifying them as national, '
                           'state/regional, or registered-unrecognised (RUPP), and '
                           'acting as a quasi-judicial body on related disputes; and '
                           '(4) Ensuring free and fair elections through inclusive '
                           'initiatives — ETPBS for service voters, the Voter Helpline '
                           'app, the Saksham app for persons with disabilities, cVIGIL '
                           'for reporting Model Code of Conduct violations, ERONET and '
                           'Suvidha for administration, and home voting for senior '
                           'citizens above 85 and PwDs (first used nationwide in the '
                           "2024 General Elections). India's over 96.8 crore (2024) "
                           'eligible voters make this one of the largest democratic '
                           'exercises in the world.',
                   'short_note': '• Est. 25 Jan 1950; Constitutional basis: Articles '
                                 '324–329.\n'
                                 '• State-level: Chief Electoral Officer, District '
                                 'Election Officers, Returning Officers.\n'
                                 '• Functions: electoral rolls (+ SIR), election '
                                 'schedule, party registration/symbols, ensuring free '
                                 '& fair polls.\n'
                                 '• Digital tools: ETPBS, Voter Helpline app, Saksham '
                                 'app (PwD), cVIGIL, ERONET, Suvidha, Sugam.\n'
                                 '• Inclusion: home voting for 85+ & PwDs (since 2024 '
                                 'General Elections).\n'
                                 "• 96.8 crore+ eligible voters (2024) — world's "
                                 'largest democratic exercise.',
                   'features': ['Creates and maintains the electoral roll (incl. '
                                'Special Intensive Revision / SIR)',
                                'Decides the election schedule',
                                'Registers political parties and allocates symbols',
                                'Works to ensure free, fair and inclusive elections '
                                '(ETPBS, Voter Helpline, Saksham, cVIGIL, home voting '
                                'for 85+/PwDs)'],
                   'keywords': ['1950',
                                'autonomous',
                                'body',
                                'commission',
                                'conducts',
                                'constitutional',
                                'control',
                                'direction',
                                'election',
                                'elections',
                                'functions',
                                'india',
                                'oversees',
                                'parishad',
                                'president',
                                'rajya',
                                'responsible',
                                'sabha',
                                'superintendence',
                                'that',
                                'vice',
                                'vidhan']},
 'economics_intro': {'chapter': '8. Building Blocks in Economics: The Problem of '
                                'Choice',
                     'aliases': ['what does economics deal with',
                                 'what is economics',
                                 'needs and wants'],
                     'definition': "Economics comes from the Greek 'oikonomia' "
                                   '(household management); it studies how limited '
                                   'resources are used to satisfy unlimited wants.',
                     'short': 'Economics is the study of how individuals, enterprises '
                              'and governments make choices to use limited resources '
                              'to satisfy unlimited human wants.',
                     'medium': 'The word Economics comes from the Greek oikonomia — '
                               "oikos ('household') + nemein ('management') — so it "
                               'literally means household management. Since resources '
                               'have competing uses, individuals, enterprises and '
                               'governments must decide how best to allocate them, '
                               'because these decisions affect the well-being of '
                               'people and society. Human preferences are divided into '
                               'needs (essentials like food, water, shelter) and wants '
                               '(gadgets, vacations, luxuries), and wants are '
                               'unlimited and keep changing (e.g., wanting to upgrade '
                               'from a bicycle to a motorbike to a car).',
                     'long': 'Economics explains how economic entities — consumers, '
                             'producers, governments and financial institutions — '
                             'interact: how people work and earn wages, how wealth is '
                             'distributed, how prices are determined, and how policy '
                             'and trade influence employment and prices. Good economic '
                             'decisions rely on data and analysis, not guesswork — '
                             'families allocate money between essentials, '
                             'non-essentials and savings; governments use tax revenue '
                             'to plan spending; enterprises study market trends to '
                             'maximise profits; and economists use data (e.g., the '
                             "government's annual Economic Survey of India, presented "
                             'before the Union Budget) to study opportunity costs and '
                             "outcomes. Economists' work spans policy-making "
                             '(taxation/welfare), business consulting, research and '
                             'education, and finance.',
                     'short_note': "• Economics = Greek 'oikonomia' (oikos = household "
                                   '+ nemein = management).\n'
                                   '• Needs (essentials) vs Wants (unlimited, '
                                   'ever-changing).\n'
                                   '• Economic entities: consumers, producers, '
                                   'governments, financial institutions.\n'
                                   '• Good decisions need data (e.g., Economic Survey '
                                   'of India, released before the Union Budget).\n'
                                   "• Scope of economists' work: policy-making, "
                                   'business consulting, research/education, finance.',
                     'keywords': ['choices',
                                  'comes',
                                  'deal',
                                  'does',
                                  'economics',
                                  'enterprises',
                                  'from',
                                  'governments',
                                  'greek',
                                  'household',
                                  'human',
                                  'individuals',
                                  'intro',
                                  'limited',
                                  'make',
                                  'management',
                                  'needs',
                                  'oikonomia',
                                  'resources',
                                  'satisfy',
                                  'studies',
                                  'study',
                                  'unlimited',
                                  'used',
                                  'wants',
                                  'what',
                                  'with']},
 'opportunity_cost': {'chapter': '8. Building Blocks in Economics: The Problem of '
                                 'Choice',
                      'aliases': ['opportunity cost',
                                  'production possibility curve',
                                  'ppc'],
                      'definition': 'The value of the next-best alternative given up '
                                    'when a choice is made.',
                      'short': 'Opportunity cost is the value of the best alternative '
                               'you give up when you choose one option over another, '
                               'because resources are limited.',
                      'medium': 'Because resources (land, labour, capital, technology) '
                                'are limited but can be put to many alternative uses, '
                                'choosing one option means giving up another — the '
                                'value of what is given up is the opportunity cost. '
                                'For example, a farmer with limited land, water and '
                                'labour choosing to grow more barley must give up some '
                                'wheat production — that forgone wheat is the '
                                'opportunity cost of the extra barley.',
                      'long': 'The Production Possibility Curve (PPC) illustrates '
                              'opportunity cost graphically: it shows the different '
                              'combinations of two goods (e.g., barley and wheat) that '
                              'can be produced using all available resources '
                              'efficiently. As a producer moves along the curve to '
                              'produce more of one good, they must produce less of the '
                              'other — the downward-sloping curve shows this '
                              'trade-off. All points ON the PPC represent maximum '
                              'efficient output (no wastage); points below it mean '
                              'resources are being under-used, and points beyond it '
                              'are currently unattainable. The PPC helps enterprises '
                              'and governments plan and make decisions by making the '
                              'cost of every choice visible.',
                      'short_note': '• Opportunity cost = value of the next-best '
                                    'alternative forgone.\n'
                                    '• Arises because resources are limited but have '
                                    'competing uses.\n'
                                    '• PPC = graph showing max combinations of 2 goods '
                                    'producible with given resources; downward-sloping '
                                    '= trade-off.\n'
                                    '• On the curve = efficient/full use of resources; '
                                    'inside = under-utilisation; outside = currently '
                                    'unattainable.',
                      'keywords': ['alternative',
                                   'another',
                                   'because',
                                   'best',
                                   'choice',
                                   'choose',
                                   'cost',
                                   'curve',
                                   'give',
                                   'given',
                                   'limited',
                                   'made',
                                   'next-best',
                                   'opportunity',
                                   'option',
                                   'over',
                                   'possibility',
                                   'production',
                                   'resources',
                                   'value',
                                   'when']},
 'key_economic_questions': {'chapter': '8. Building Blocks in Economics: The Problem '
                                       'of Choice',
                            'aliases': ['what how for whom to produce',
                                        'key questions in economics',
                                        'economic systems',
                                        'planned market mixed economy'],
                            'definition': 'The three key questions economics answers: '
                                          'What to produce, How to produce, and For '
                                          'Whom to produce.',
                            'short': 'Every economy must answer three key questions — '
                                     'What to produce, How to produce, and For Whom to '
                                     'produce — because wants are unlimited but '
                                     'resources are scarce.',
                            'medium': 'The mismatch between unlimited wants and '
                                      'limited resources creates scarcity, which '
                                      'forces choices, giving rise to three key '
                                      'economic questions: (1) What to produce — e.g., '
                                      'should farmers grow water-intensive sugarcane '
                                      '(high profit) or drought-resistant millets '
                                      '(sustainable, saves water)? (2) How to produce '
                                      '— should production be labour-intensive or '
                                      'capital-intensive, depending on cost of '
                                      'capital, technology level, and nature of the '
                                      'product? (3) For whom to produce — producers '
                                      'target different consumer groups by income, '
                                      'needs and taste (e.g., school shoes vs '
                                      'office-wear shoes vs sports shoes).',
                            'long': 'How an economy answers these three questions '
                                    'depends on its economic system: (1) Planned '
                                    'economy — a central government authority decides '
                                    'what/how/for whom, owns most resources (land, '
                                    'factories, banks), and heavily regulates '
                                    'enterprises through permits; limits competition '
                                    'and innovation (e.g., former Soviet Union, North '
                                    'Korea, Cuba). (2) Market economy — demand and '
                                    'supply, with private ownership of resources, '
                                    'decide production; government acts like a referee '
                                    'ensuring law and order without controlling '
                                    'prices; competition drives quality/innovation '
                                    '(e.g., USA, Japan, Hong Kong). (3) Mixed economy '
                                    '— combines both: private individuals/enterprises '
                                    'and government share economic decision-making, '
                                    'with government ensuring fair competition, '
                                    'consumer protection, transparency, public goods '
                                    'and welfare programmes, while the market drives '
                                    'profit-making, innovation and competition (e.g., '
                                    'India post-1991, China post-1978, Germany, '
                                    'Sweden). India moved from a more '
                                    'state-led/planned approach after Independence to '
                                    'a more market-oriented mixed economy after the '
                                    '1991 economic reforms.',
                            'short_note': '• Scarcity (unlimited wants + limited '
                                          'resources) → 3 key questions: What / How / '
                                          'For Whom to produce.\n'
                                          "• 'What' e.g.: sugarcane (profit) vs "
                                          'millets (sustainability).\n'
                                          "• 'How': labour-intensive vs "
                                          'capital-intensive.\n'
                                          "• 'For whom': targeting consumer groups by "
                                          'income/need/taste.\n'
                                          '• 3 economic systems: Planned '
                                          '(govt-controlled; USSR, N. Korea, Cuba), '
                                          'Market (demand-supply driven; USA, Japan, '
                                          'Hong Kong), Mixed (both; India post-1991, '
                                          'China post-1978, Germany, Sweden).\n'
                                          '• India: planned-style (post-Independence) '
                                          '→ mixed/market-oriented (post-1991 '
                                          'reforms).',
                            'features': ['What to produce — deciding which '
                                         'goods/services and how much, given '
                                         'trade-offs (e.g., sugarcane vs millets)',
                                         'How to produce — choosing labour-intensive '
                                         'vs capital-intensive methods based on cost '
                                         'of capital, technology, and product type',
                                         'For whom to produce — targeting different '
                                         'consumer groups by income, need and taste'],
                            'keywords': ['answer',
                                         'answers',
                                         'because',
                                         'economic',
                                         'economics',
                                         'economy',
                                         'every',
                                         'market',
                                         'mixed',
                                         'must',
                                         'planned',
                                         'produce',
                                         'questions',
                                         'resources',
                                         'scarce',
                                         'systems',
                                         'three',
                                         'unlimited',
                                         'wants',
                                         'what',
                                         'whom']},
 'demand_supply': {'chapter': '9. The Price Puzzle: What Drives the Market',
                   'aliases': ['demand and supply',
                               'law of demand',
                               'law of supply',
                               'determinants of demand',
                               'determinants of supply'],
                   'definition': 'Demand is the quantity of a good buyers are '
                                 'willing/able to buy at a price; supply is the '
                                 'quantity sellers are willing/able to sell at a '
                                 'price.',
                   'short': 'Demand and supply are the two forces that determine '
                            'market prices: demand usually falls as price rises, while '
                            'supply usually rises as price rises.',
                   'medium': 'Demand is the quantity of a good or service consumers '
                             'are willing and able to buy at a given price in a given '
                             'period; normally, demand falls as price rises and rises '
                             'as price falls. Besides price, demand is affected by '
                             'other determinants — price of related '
                             '(substitute/complementary) goods, income, taste and '
                             'preference of buyers, and seasonality (e.g., crowded '
                             'bookshops at the start of a new school year). Supply is '
                             'the quantity producers are willing and able to sell at a '
                             'given price; supply usually rises as price rises. Supply '
                             'is also affected by other determinants — price of '
                             'related goods, number of sellers in the market, and '
                             'technology.',
                   'long': 'When plotted, demand and supply schedules give demand and '
                           'supply curves — the demand curve typically slopes downward '
                           '(price ↓ → quantity demanded ↑) and the supply curve '
                           'typically slopes upward (price ↑ → quantity supplied ↑). '
                           'The point where the two curves intersect is the '
                           'equilibrium price and quantity — where quantity demanded '
                           'equals quantity supplied. If price is set above '
                           'equilibrium, supply exceeds demand (excess '
                           'supply/surplus); if set below equilibrium, demand exceeds '
                           'supply (excess demand/shortage). Governments sometimes '
                           'intervene with a price floor (a minimum price, set above '
                           'equilibrium, e.g., to protect producers) or a price '
                           'ceiling (a maximum price, set below equilibrium, e.g., to '
                           'protect consumers), and regulate unfair market practices '
                           'to protect both buyers and sellers.',
                   'short_note': '• Law of demand: price ↑ → quantity demanded ↓ '
                                 '(usually), all else constant.\n'
                                 '• Law of supply: price ↑ → quantity supplied ↑ '
                                 '(usually).\n'
                                 '• Demand determinants (besides price): price of '
                                 'related goods, income, taste/preference, '
                                 'seasonality.\n'
                                 '• Supply determinants (besides price): price of '
                                 'related goods, number of sellers, technology.\n'
                                 '• Equilibrium = point where demand curve meets '
                                 'supply curve (Qd = Qs).\n'
                                 '• Price above equilibrium → excess supply; price '
                                 'below equilibrium → excess demand.\n'
                                 '• Govt tools: price floor (minimum, protects '
                                 'producers), price ceiling (maximum, protects '
                                 'consumers).',
                   'keywords': ['buyers',
                                'demand',
                                'determinants',
                                'determine',
                                'falls',
                                'forces',
                                'good',
                                'market',
                                'price',
                                'prices',
                                'quantity',
                                'rises',
                                'sell',
                                'sellers',
                                'supply',
                                'that',
                                'usually',
                                'while',
                                'willing/able']},
 'market_equilibrium': {'chapter': '9. The Price Puzzle: What Drives the Market',
                        'aliases': ['market equilibrium',
                                    'equilibrium price',
                                    'excess demand',
                                    'excess supply',
                                    'does equilibrium exist in real world'],
                        'definition': 'The price at which quantity demanded equals '
                                      'quantity supplied, so there is neither a '
                                      'shortage nor a surplus.',
                        'short': 'Market equilibrium is the point where quantity '
                                 'demanded equals quantity supplied — at that price, '
                                 'there is no shortage or surplus, and prices have no '
                                 'pressure to change.',
                        'medium': 'Prices are determined by negotiation between what '
                                  'buyers are willing to pay and what sellers are '
                                  'willing to accept — i.e., by the interaction of '
                                  'demand and supply. For example, at ₹40, mangoes see '
                                  '38 kg demanded but only 6 kg supplied — excess '
                                  'demand (shortage, Qd > Qs). At ₹150, 8 kg are '
                                  'demanded but 43 kg supplied — excess supply '
                                  '(surplus, Qs > Qd). At ₹100, 12 kg are both '
                                  'demanded and supplied — this is the equilibrium '
                                  'price (₹100) and equilibrium quantity (12 kg), the '
                                  'point where the demand curve and supply curve '
                                  'intersect on a graph.',
                        'long': 'In theory, equilibrium is a single intersection '
                                'point, but real markets are dynamic — changing '
                                'technology, wages, interest rates, wars, political '
                                'events, pandemics, weather and disasters continuously '
                                'shift demand and supply, so the market is always '
                                'adjusting toward a new equilibrium rather than '
                                'staying fixed at one (e.g., face-mask demand surged '
                                'in the COVID-19 pandemic of 2020, pushing prices up '
                                'until supply caught up, after which prices fell '
                                'back). Hotel room tariffs illustrate this well: the '
                                'same 100-room hotel in Goa might charge ₹1,500/night '
                                'on an off-season weekday, ₹8,000/night on a '
                                'tourist-season weekend, and ₹25,000/night on New '
                                "Year's Eve — prices shift with demand, season, "
                                'competitor pricing, events, weather, and booking '
                                'trends.',
                        'short_note': '• Equilibrium price/quantity = where Qd = Qs '
                                      '(demand curve meets supply curve).\n'
                                      '• Price BELOW equilibrium → Qd > Qs → excess '
                                      'demand/shortage.\n'
                                      '• Price ABOVE equilibrium → Qs > Qd → excess '
                                      'supply/surplus.\n'
                                      '• Textbook example: mangoes — ₹40 (excess '
                                      'demand), ₹100 (equilibrium, 12 kg), ₹150 '
                                      '(excess supply).\n'
                                      '• Real-world equilibrium is dynamic, not fixed '
                                      '— shifts with tech, wages, interest rates, '
                                      'disasters, pandemics (e.g., COVID-19 masks), '
                                      'and demand cycles (e.g., hotel tariffs by '
                                      'season/event).',
                        'keywords': ['change',
                                     'demand',
                                     'demanded',
                                     'does',
                                     'equals',
                                     'equilibrium',
                                     'excess',
                                     'exist',
                                     'have',
                                     'market',
                                     'neither',
                                     'point',
                                     'pressure',
                                     'price',
                                     'prices',
                                     'quantity',
                                     'real',
                                     'shortage',
                                     'supplied',
                                     'supply',
                                     'surplus',
                                     'that',
                                     'there',
                                     'where',
                                     'which',
                                     'world']},
 'price_floor_ceiling': {'chapter': '9. The Price Puzzle: What Drives the Market',
                         'aliases': ['price floor',
                                     'price ceiling',
                                     'government intervention in market',
                                     'minimum price maximum price',
                                     'regulation of unfair practices'],
                         'definition': 'A price ceiling is a government-imposed '
                                       'MAXIMUM price (protects consumers); a price '
                                       'floor is a government-imposed MINIMUM price '
                                       '(protects producers/workers).',
                         'short': 'Governments intervene in markets with a price '
                                  'ceiling (a maximum price, to keep essentials '
                                  'affordable) or a price floor (a minimum price, to '
                                  "protect producers or workers), since markets don't "
                                  'always allocate fairly on their own.',
                         'medium': 'India is a market-based, regulated economy (the '
                                   "world's fourth largest) where prices generally "
                                   'depend on demand and supply — but markets allocate '
                                   'goods based on willingness and ability to pay, '
                                   'which can be unfair (e.g., if essential medicines '
                                   'become very expensive, poorer people may be priced '
                                   'out). So the government regulates unfair practices '
                                   'to protect consumers, workers and producers: a '
                                   'price ceiling sets the maximum a seller can charge '
                                   '(e.g., capping medicine prices to prevent '
                                   'overcharging), while a price floor sets the '
                                   'minimum that can be charged (e.g., a minimum wage, '
                                   'to ensure workers earn enough) — for a price floor '
                                   'to be effective, it must be set above the market '
                                   'equilibrium price.',
                         'long': 'Price ceiling: an imposed maximum price — set BELOW '
                                 'equilibrium — used to keep essential goods/services '
                                 'accessible (e.g., medicines); risk: can cause '
                                 'shortages if suppliers are unwilling to sell at the '
                                 'capped price. Price floor: an imposed minimum price '
                                 '— set ABOVE equilibrium to be effective — used to '
                                 'protect producers or workers (e.g., minimum wage '
                                 'laws); risk: can cause surplus/unsold stock. Both '
                                 'are examples of the government stepping in because '
                                 'markets, left alone, allocate purely by purchasing '
                                 'power/willingness to pay, which does not guarantee '
                                 'fairness or welfare for vulnerable and low-income '
                                 'groups. Beyond price controls, this also includes '
                                 'action against monopolies (a market dominated by a '
                                 'single seller) and other unfair practices.',
                         'short_note': '• Price ceiling = govt-set MAXIMUM price, '
                                       'below equilibrium (e.g., medicine price caps) '
                                       '→ protects consumers; risk = shortage.\n'
                                       '• Price floor = govt-set MINIMUM price, must '
                                       'be above equilibrium to work (e.g., minimum '
                                       'wage) → protects producers/workers; risk = '
                                       'surplus.\n'
                                       '• Why intervene: markets allocate by '
                                       'willingness/ability to pay, which can be '
                                       'unfair to low-income/vulnerable groups.\n'
                                       '• India = market-based, regulated economy; '
                                       "world's 4th-largest economy.\n"
                                       '• Monopoly = market dominated by a single '
                                       'seller — another target of govt regulation.',
                         'keywords': ['affordable',
                                      'allocate',
                                      'always',
                                      'ceiling',
                                      'consumers',
                                      "don't",
                                      'essentials',
                                      'fairly',
                                      'floor',
                                      'government',
                                      'government-imposed',
                                      'governments',
                                      'intervene',
                                      'intervention',
                                      'keep',
                                      'market',
                                      'markets',
                                      'maximum',
                                      'minimum',
                                      'practices',
                                      'price',
                                      'producers',
                                      'producers/workers',
                                      'protect',
                                      'protects',
                                      'regulation',
                                      'since',
                                      'their',
                                      'unfair',
                                      'with',
                                      'workers']},
 'monopoly_market_structure': {'chapter': '9. The Price Puzzle: What Drives the '
                                          'Market',
                               'aliases': ['monopoly',
                                           'what is monopoly',
                                           'single seller market',
                                           'hoarding and black marketing',
                                           'essential commodities act'],
                               'definition': 'A monopoly is a market structure with a '
                                             'single seller or producer controlling '
                                             'the entire supply of a unique product or '
                                             'service, facing no close substitutes, '
                                             'giving it significant power to set '
                                             'prices and output.',
                               'short': 'A monopoly is a market with a single seller '
                                        'controlling the entire supply of a product, '
                                        'giving it the power to charge higher prices '
                                        'and restrict supply — which is why '
                                        'governments regulate such markets.',
                               'medium': 'A monopoly is a market structure with a '
                                         'single seller or producer controlling the '
                                         'entire supply of a unique product or '
                                         'service, facing no close substitutes, and '
                                         'therefore having significant power to set '
                                         'prices and output. Sometimes a single or a '
                                         'few sellers dominate a market and can charge '
                                         'higher prices and supply less than a '
                                         'competitive market would — this is '
                                         'detrimental to consumer welfare, as such '
                                         'sellers may charge higher prices, provide '
                                         'poorer-quality goods and services, or '
                                         'restrict supply. The government therefore '
                                         'regulates such practices by keeping prices '
                                         'and quantity supplied in check.',
                               'long': 'A monopoly is a market structure with a single '
                                       'seller or producer controlling the entire '
                                       'supply of a unique product or service, facing '
                                       'no close substitutes, and having significant '
                                       'power to set prices and output. Left '
                                       'unchecked, this form of market power can harm '
                                       'consumer welfare — a monopolist may charge '
                                       'higher prices, supply lower-quality goods and '
                                       'services, or restrict supply below what a '
                                       'competitive market would offer. This is one '
                                       'reason the government regulates unfair market '
                                       'practices, alongside tools like the price '
                                       'ceiling and price floor. A related unfair '
                                       'practice is hoarding — the accumulation of '
                                       'goods, commodities, or money by traders, '
                                       'usually to create scarcity and push up prices. '
                                       'During the COVID-19 pandemic, demand for '
                                       'sanitisers surged, leading to stockouts and '
                                       'sharp price increases; some shopkeepers began '
                                       'hoarding and black-marketing, and the '
                                       'government intervened by declaring sanitisers '
                                       'an essential commodity under the Essential '
                                       'Commodities Act, allowing it to regulate '
                                       'production, supply and pricing to protect '
                                       'consumers.',
                               'short_note': '• Monopoly = market structure with a '
                                             'SINGLE seller/producer controlling the '
                                             'entire supply of a unique product; no '
                                             'close substitutes; strong power over '
                                             'price & output.\n'
                                             '• Harm: can mean higher prices, poorer '
                                             'quality, restricted supply → govt '
                                             'regulates prices/quantity to protect '
                                             'consumers.\n'
                                             '• Hoarding = accumulating goods/'
                                             'commodities/money (often to create '
                                             'scarcity & raise prices) — an unfair '
                                             'practice.\n'
                                             '• Case study: COVID-19 sanitiser '
                                             'shortage → hoarding/black-marketing → '
                                             'govt declared sanitisers an essential '
                                             'commodity under the Essential '
                                             'Commodities Act to regulate them.',
                               'keywords': ['black-marketing',
                                            'commodities',
                                            'covid-19',
                                            'essential',
                                            'hoarding',
                                            'market',
                                            'monopoly',
                                            'price',
                                            'producer',
                                            'sanitisers',
                                            'seller',
                                            'single',
                                            'structure',
                                            'substitutes',
                                            'supply']},
 'government_role_in_economy': {'chapter': '9. The Price Puzzle: What Drives the '
                                           'Market',
                                'aliases': ['role of government in economy',
                                            'economic regulators in india',
                                            'rbi trai sebi',
                                            'consumer protection',
                                            'government regulation of market'],
                                'definition': "India is a market-based, regulated "
                                              'economy — prices generally depend on '
                                              'demand and supply, but the government '
                                              'intervenes and regulates through '
                                              'bodies like the RBI, CCPA, TRAI and '
                                              'SEBI to protect fairness.',
                                'short': 'India is a market-based, regulated economy '
                                         '(the fourth largest in the world); since '
                                         'markets do not always allocate fairly, the '
                                         'government regulates through bodies like '
                                         'the RBI, CCPA, TRAI and SEBI.',
                                'medium': 'Today, India is the fourth-largest economy '
                                          'in the world — a market-based, regulated '
                                          'economy in which prices depend on demand '
                                          'and supply. However, markets do not always '
                                          'work fairly, since they allocate goods and '
                                          'services based on willingness and ability '
                                          'to pay (e.g., if essential medicines '
                                          'become very expensive, they may not be '
                                          'accessible to all). So the government '
                                          'plays an important role in the economy: it '
                                          'regulates unfair practices (price '
                                          'ceilings/floors, action on monopolies), '
                                          'and works through regulators such as the '
                                          'Reserve Bank of India (RBI) for banking, '
                                          'the Central Consumer Protection Authority '
                                          '(CCPA) for consumer-rights violations and '
                                          'unfair trade practices, the Telecom '
                                          'Regulatory Authority of India (TRAI) for '
                                          'telecommunications, and the Securities and '
                                          'Exchange Board of India (SEBI) for the '
                                          'securities market, to ensure transparency.',
                                'long': 'India is a market-based, regulated economy '
                                        'and, as of the time of writing, the '
                                        "fourth-largest economy in the world; prices "
                                        'generally depend on demand and supply, but '
                                        'markets do not always work fairly because '
                                        'they allocate goods and services purely on '
                                        'the basis of willingness and ability to pay. '
                                        'If essential goods such as medicines become '
                                        'very expensive, they may become inaccessible '
                                        'to poorer or vulnerable groups; fairness and '
                                        'equity in allocation are especially '
                                        'important for such groups. The government '
                                        'therefore plays an important role in the '
                                        'economy, primarily through the Regulation '
                                        'of Unfair Practices — protecting consumers, '
                                        'workers, and producers from exploitation and '
                                        'injustice. This includes setting price '
                                        'ceilings (maximum prices) for essential '
                                        'goods like medicines to prevent '
                                        'overcharging, and setting a price floor '
                                        '(minimum wage) to ensure workers earn '
                                        'enough. Many specialised regulators support '
                                        'this role and ensure transparency in '
                                        'different sectors of the market: the Reserve '
                                        'Bank of India (RBI) for banking, the Central '
                                        'Consumer Protection Authority (CCPA) for '
                                        'violations of consumer rights and unfair '
                                        'trade practices, the Telecom Regulatory '
                                        'Authority of India (TRAI) for the '
                                        'telecommunications sector, and the '
                                        'Securities and Exchange Board of India '
                                        '(SEBI) for the securities market. The '
                                        'government also acts against monopolies (a '
                                        'single or few sellers dominating a market) '
                                        'and unfair practices like hoarding — for '
                                        'example, during the COVID-19 pandemic, '
                                        'surging demand for sanitisers led to '
                                        'stockouts, price increases, hoarding and '
                                        'black-marketing, and the government '
                                        'responded by declaring sanitisers an '
                                        'essential commodity under the Essential '
                                        'Commodities Act, so their production, supply '
                                        'and pricing could be regulated.',
                                'short_note': '• India = market-based, regulated '
                                              "economy; world's 4th-largest economy "
                                              '(at time of writing).\n'
                                              '• Why regulate: markets allocate '
                                              'purely by willingness/ability to pay → '
                                              'can be unfair to poor/vulnerable '
                                              'groups.\n'
                                              '• Tools: price ceiling (max price, '
                                              'e.g. medicines), price floor (min '
                                              'price, e.g. minimum wage), action '
                                              'against monopolies & hoarding.\n'
                                              '• Key regulators: RBI (banking), CCPA '
                                              '(consumer protection/unfair trade), '
                                              'TRAI (telecom), SEBI (securities '
                                              'market).\n'
                                              '• Case study: COVID-19 sanitiser '
                                              'shortage → hoarding/black-marketing → '
                                              'declared essential commodity under the '
                                              'Essential Commodities Act.',
                                'features': ['Regulation of unfair practices — '
                                             'protects consumers, workers and '
                                             'producers (price ceilings, price '
                                             'floors)',
                                             'Sector regulators — RBI (banking), CCPA '
                                             '(consumer protection), TRAI (telecom), '
                                             'SEBI (securities market)',
                                             'Action against monopolies and practices '
                                             'like hoarding/black-marketing',
                                             'Powers under laws like the Essential '
                                             'Commodities Act to regulate production, '
                                             'supply and pricing of essential goods'],
                                'keywords': ['ccpa',
                                             'economy',
                                             'fairness',
                                             'fourth-largest',
                                             'government',
                                             'market-based',
                                             'rbi',
                                             'regulated',
                                             'regulators',
                                             'role',
                                             'sebi',
                                             'trai']}}


# ---------------------------------------------------------------------------
# 2. NORMALISATION HELPERS
# ---------------------------------------------------------------------------

_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)
_SPACE_RE = re.compile(r"\s+")

# Small, curated list of common typo corrections for words that show up a
# lot in this KB — NOT a general spellchecker, just enough to make everyday
# student typos land on the right topic. (Anything else is handled by the
# per-word fuzzy matching in _token_score.)
_SPELL_FIXES = {
    "democrcy": "democracy", "democrasy": "democracy", "demokrasy": "democracy",
    "democracey": "democracy", "democrecy": "democracy",
    "electon": "election", "electons": "elections", "electoin": "election",
    "elction": "election", "eletion": "election", "elections": "elections",
    "econimics": "economics", "econmics": "economics", "eceonomics": "economics",
    "econamy": "economy", "econmy": "economy",
    "athmosphere": "atmosphere", "atmoshpere": "atmosphere",
    "atmosfer": "atmosphere", "amosphere": "atmosphere",
    "monsoom": "monsoon", "monsun": "monsoon", "mansoon": "monsoon",
    "monsson": "monsoon",
    "civilisaton": "civilisation", "civilization": "civilisation",
    "oppurtunity": "opportunity", "oportunity": "opportunity",
    "opertunity": "opportunity",
    "equilibrum": "equilibrium", "equlibrium": "equilibrium",
    "monoply": "monopoly", "monopli": "monopoly",
    "harrapan": "harappan", "harapan": "harappan",
}

# Base stop-words: ALWAYS stripped from a query before topic matching.
# (question words, grammar glue, and the old "type/mode" words.)
_STOPWORDS = {
    "what", "is", "are", "the", "a", "an", "of", "do", "you", "mean",
    "by", "explain", "define", "definition", "tell", "me", "about",
    "give", "write", "short", "note", "notes", "on", "in", "detail",
    "details", "detailed", "long", "medium", "brief", "briefly",
    "please", "can", "how", "why", "does", "did", "for", "to", "and",
    "describe", "meaning", "significance", "importance", "important",
    "features", "feature", "characteristics", "main", "causes", "cause",
    "effects", "effect", "example", "examples", "some", "few", "with",
    "from", "as", "it", "its", "this", "that",
    # interrogatives / grammar glue
    "when", "where", "which", "who", "whom", "whose", "if", "then", "than",
    "so", "but", "or", "not", "no", "yes", "was", "were", "be", "been",
    "being", "am", "has", "have", "had", "having", "i", "my", "we", "our",
    "us", "your", "yours", "they", "them", "he", "she", "at", "into",
    "onto", "upon", "any", "all", "also", "too", "very", "just", "only",
    "more", "most", "meant", "means", "explanation", "explanations",
    # common typos of question words
    "wat", "wht", "whts", "whats", "explane", "explian", "defne", "definne",
    "discribe", "descibe", "plz", "pls", "wats",
}

# Extra "filler" words used when people phrase questions in different ways
# (polite forms, exam wording, Hinglish, etc). They are stripped ONLY when
# they are not themselves part of some topic's vocabulary — so a word like
# "types" or "role", which is part of real topic names, is never lost.
_FILLER = {
    # request / politeness
    "discuss", "elaborate", "enumerate", "mention", "state", "name", "list",
    "teach", "learn", "understand", "understanding", "know", "knowledge",
    "want", "wanna", "need", "needs", "help", "show", "provide", "get",
    "find", "kindly", "could", "would", "should", "will", "shall", "may",
    "might", "must", "let", "lets", "like", "sir", "madam", "mam", "bhai",
    "dear", "ai", "sst", "hey", "hello", "hi", "hii", "excuse", "doubt",
    "quick", "quickly", "question", "questions", "ques", "ans", "answer",
    "answers", "q", "exam", "test", "paper", "board", "ncert", "cbse",
    "class", "grade", "chapter", "topic", "topics", "concept", "concepts",
    "term", "terms", "overview", "introduction", "intro", "summary",
    "summarise", "summarize", "revise", "revision", "cheat", "sheet",
    "flashcard", "points", "point", "bullet", "bullets", "pointwise",
    "key", "simple", "simply", "easy", "easily", "words", "language",
    "beginners", "layman", "eli5", "marks", "mark", "essay", "paragraph",
    "one", "two", "three", "line", "lines", "sentence", "word",
    # exam-style words
    "mcq", "fill", "blanks", "blank", "choose", "correct", "option", "match",
    "following", "assertion", "reason", "statement", "true", "false",
    "case", "study", "based", "application", "situation", "situational",
    "hots", "higher", "order", "thinking", "very", "long", "short",
    # relations
    "regarding", "concerning", "related", "around", "between", "among",
    "information", "facts", "fact", "fun", "something", "everything",
    "anything", "nutshell", "full", "complete", "thoroughly", "depth",
    "example", "instance", "illustrate", "illustrated",
    # Hinglish glue
    "kya", "hai", "hain", "hota", "hoti", "hote", "kyu", "kyun", "kyon",
    "kaise", "kaisa", "kaun", "kab", "kahan", "kitna", "batao", "bataiye",
    "bataye", "samjhao", "samjhaiye", "samjha", "matlab", "arth", "ke",
    "ki", "ka", "ko", "se", "mein", "me", "par", "aur", "ya", "yeh", "ye",
    "woh", "wo", "mujhe", "mujhko", "hume", "hamein", "humein", "tum",
    "aap", "bare", "baare", "baarein", "wale", "wala", "vishay",
    "jaankari", "jankari", "likho", "likhiye", "karo", "kariye", "hoga",
    "hua", "hui", "hue", "mahatva", "visheshta", "visheshtayein", "karan",
    "prabhav", "udaharan", "paribhasha", "zaroori", "jaruri", "antar",
    "fark", "batana", "batado", "bata", "do", "dijiye", "chahiye",
    # casual add-ons students tack on
    "thanks", "thank", "urgent", "fast", "today", "tomorrow", "asap",
    "tonight", "now", "soon", "before", "after", "again", "okay", "ok",
    "bro", "yaar", "actually", "basically", "really", "exactly",
}


def _normalise(text: str) -> str:
    text = text.lower().strip()
    text = _PUNCT_RE.sub(" ", text)
    text = _SPACE_RE.sub(" ", text).strip()
    return text


def _fix_spelling(word: str) -> str:
    return _SPELL_FIXES.get(word, word)


def _singularise(word: str) -> str:
    """Very small heuristic: strip a trailing 's' for matching purposes
    only (never mutates stored data), so 'elections' ~ 'election'."""
    if len(word) > 4 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _tokenise(text: str) -> set[str]:
    words = _normalise(text).split()
    return {_singularise(_fix_spelling(w)) for w in words if len(w) > 2}


# Let a chapter be askable by its own title too, e.g. "the price puzzle" or
# "shaping of the earth's surface" — mapped onto that chapter's first/most
# central topic, so students who only remember the chapter name (not a
# specific concept inside it) still get a sensible answer.
_CHAPTER_REPRESENTATIVE: dict[str, str] = {}
# Bare chapter-title aliases (e.g. "Democracy", "Elections") are tracked
# separately per topic key. They are deliberately short/generic — a query
# like "challenges to indian democracy" contains the word "democracy" but
# is clearly NOT asking for the whole chapter. So these bare-title aliases
# may only win stage-1 matching on an EXACT phrase match (see find_topic),
# never on substring containment.
_CHAPTER_TITLE_ALIASES: dict[str, set[str]] = {}
for _key, _entry in KB.items():
    _chapter_title = _entry.get("chapter", "")
    if _chapter_title and _chapter_title not in _CHAPTER_REPRESENTATIVE:
        _CHAPTER_REPRESENTATIVE[_chapter_title] = _key
        _bare_title = re.sub(r"^\d+\.\s*", "", _chapter_title)
        _entry.setdefault("aliases", [])
        if _bare_title.lower() not in [a.lower() for a in _entry["aliases"]]:
            _entry["aliases"].append(_bare_title)
        _CHAPTER_TITLE_ALIASES.setdefault(_key, set()).add(_bare_title.lower())

_TOPIC_PHRASES: dict[str, list[str]] = {}
_TOPIC_ALIAS_STRINGS: dict[str, list[str]] = {}
_TOPIC_TOKENS: dict[str, set[str]] = {}

for _key, _entry in KB.items():
    _TOPIC_PHRASES[_key] = [_key.replace("_", " ")] + list(_entry.get("aliases", []))
    _bag = list(_TOPIC_PHRASES[_key]) + list(_entry.get("keywords", []))
    _TOPIC_ALIAS_STRINGS[_key] = _bag
    _tok = set()
    for _phrase in _bag:
        _tok |= _tokenise(_phrase)
    _TOPIC_TOKENS[_key] = _tok

# tokens from a topic's own name/aliases (NOT its loose keyword list) — used
# only to break ties between topics that match a query equally well.
_TOPIC_CORE_TOKENS: dict[str, set[str]] = {}
for _key in KB:
    _core = set()
    for _phrase in _TOPIC_PHRASES[_key]:
        _core |= _tokenise(_phrase)
    _TOPIC_CORE_TOKENS[_key] = _core

# every word the KB itself uses — used to protect real subject words from
# being stripped as "filler", and as the vocabulary for fuzzy matching.
_ALL_TOPIC_WORDS: frozenset = frozenset().union(*_TOPIC_TOKENS.values())

# Human-friendly names for topics (used in comparisons, quizzes, listings).
TOPIC_LABELS = {
    "social_science": "Social Science",
    "four_disciplines": "The Four Disciplines of Social Science",
    "plate_tectonics": "Plate Tectonics",
    "weathering_erosion": "Weathering and Erosion",
    "river_landforms": "River Landforms",
    "coastal_glacial_wind_groundwater_landforms":
        "Coastal, Glacial, Wind and Groundwater Landforms",
    "landforms_disasters": "Landform-related Disasters",
    "atmosphere": "The Atmosphere",
    "weather_vs_climate": "Weather and Climate",
    "monsoon": "Monsoon",
    "human_evolution": "Human Evolution",
    "stone_age_tools": "The Stone Age and Stone Tools",
    "invention_of_writing": "Invention of Writing",
    "early_civilisations": "Early Civilisations",
    "vedic_period": "The Vedic Period",
    "janapadas_mahajanapadas": "Janapadas and Mahajanapadas",
    "mauryan_administration": "Mauryan Administration (Saptanga Theory)",
    "gupta_administration": "Gupta Administration",
    "uttaramerur_village_assembly": "Uttaramerur Village Assembly (Kudavolai)",
    "dharma_chakravarti": "Dharma and Chakravarti Samrat",
    "democracy": "Democracy",
    "types_of_democracy": "Types of Democracy",
    "challenges_to_indian_democracy": "Challenges to Indian Democracy",
    "democratic_traditions_india": "Democratic Traditions in India",
    "media_role_democracy": "Role of Media in Democracy",
    "elections": "Elections",
    "eci_functions": "Election Commission of India (ECI)",
    "economics_intro": "Economics: Needs and Wants",
    "opportunity_cost": "Opportunity Cost and the PPC",
    "key_economic_questions": "Key Economic Questions and Economic Systems",
    "demand_supply": "Demand and Supply",
    "market_equilibrium": "Market Equilibrium",
    "price_floor_ceiling": "Price Floor and Price Ceiling",
    "monopoly_market_structure": "Monopoly",
    "government_role_in_economy": "Role of Government in the Economy",
}

_SUBJECT_BY_CHAPTER_NO = {
    1: "Social Science (Introduction)", 2: "Geography", 3: "Geography",
    4: "History", 5: "History", 6: "Political Science",
    7: "Political Science", 8: "Economics", 9: "Economics",
}


def topic_label(key: str) -> str:
    return TOPIC_LABELS.get(key, key.replace("_", " ").title())


def topic_subject(key: str) -> str:
    try:
        n = int(KB[key]["chapter"].split(".")[0])
    except Exception:
        return "Social Science"
    return _SUBJECT_BY_CHAPTER_NO.get(n, "Social Science")


# ---------------------------------------------------------------------------
# 3. MODE DETECTION  (short / medium / long / short_note / definition)
# ---------------------------------------------------------------------------

MODES = ("short", "medium", "long", "short_note", "definition")
DEFAULT_MODE = "medium"

_MODE_ALIASES = {
    "short": "short", "quick": "short", "brief": "short", "briefly": "short",
    "medium": "medium", "explanation": "medium",
    "long": "long", "detail": "long", "detailed": "long", "elaborate": "long",
    "short note": "short_note", "shortnote": "short_note", "note": "short_note",
    "notes": "short_note", "short_note": "short_note",
    "definition": "definition", "define": "definition", "meaning": "definition",
}

# Explicit "mode:" prefixes, e.g. "short: what is democracy"
_MODE_PREFIX_RE = re.compile(
    r"^\s*(" + "|".join(sorted(_MODE_ALIASES.keys(), key=len, reverse=True))
    + r")\s*:\s*(.+)$",
    re.IGNORECASE,
)

_NUM_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
              "six": 6, "seven": 7, "eight": 8, "ten": 10}
_MARKS_RE = re.compile(
    r"\b(\d{1,2}|one|two|three|four|five|six|seven|eight|ten)\s*[- ]?marks?\b",
    re.IGNORECASE)

# Natural-language mode hints, checked in order (first hit wins) only if
# there was no explicit "mode:" prefix and no "N marks" hint.
_NATURAL_MODE_HINTS = [
    (re.compile(r"\b(short\s+notes?|write\s+notes?|make\s+notes?|notes?\s+(on|for|of)|"
                r"revision\s+notes?|quick\s+revision|revise|revision|key\s+points?|"
                r"important\s+points?|main\s+points?|bullet(ed)?\s+points?|bullets?|"
                r"in\s+points?|point\s*wise|summary|summari[sz]e|cheat\s*sheet|"
                r"flash\s*cards?)\b", re.I), "short_note"),
    (re.compile(r"\b(in\s+detail|detailed|elaborate|elaborately|thoroughly|"
                r"in[\s-]depth|comprehensive(ly)?|everything\s+(about|on)|all\s+about|"
                r"full\s+explanation|complete\s+explanation|step\s+by\s+step|"
                r"essay|long\s+answers?|descriptive|at\s+length|explain\s+fully|"
                r"very\s+long)\b", re.I), "long"),
    (re.compile(r"\b(one\s+line|one[\s-]liner|in\s+a\s+line|one\s+sentence|"
                r"1\s+(line|sentence)|(two|2)\s+lines|in\s+short|shortly|in\s+brief|"
                r"briefly|brief|short\s+answers?|very\s+short|quick\s+answers?|"
                r"in\s+a\s+nutshell|one\s+word|simple\s+(words|terms|language)|"
                r"in\s+simple|simply|easy\s+(words|language|way)|in\s+easy|eli5|"
                r"like\s+i\s*(am|m)\s+5|for\s+beginners|layman|short)\b", re.I),
     "short"),
    (re.compile(r"\bgive\s+(a\s+)?medium\s+answer\b", re.I), "medium"),
]


def _marks_to_mode(n: int) -> str:
    if n <= 2:
        return "short"
    if n <= 4:
        return "medium"
    return "long"


def _detect_mode(raw: str) -> tuple[str | None, str]:
    """Returns (explicit_mode_or_None, remaining_text)."""
    m = _MODE_PREFIX_RE.match(raw)
    if m:
        mode_word, rest = m.group(1).lower(), m.group(2)
        return _MODE_ALIASES.get(mode_word, DEFAULT_MODE), rest.strip()

    mm = _MARKS_RE.search(raw)
    if mm:
        w = mm.group(1).lower()
        n = int(w) if w.isdigit() else _NUM_WORDS.get(w, 3)
        return _marks_to_mode(n), raw

    for pattern, mode in _NATURAL_MODE_HINTS:
        if pattern.search(raw):
            return mode, raw

    return None, raw


# ---------------------------------------------------------------------------
# 4. QUESTION-TYPE DETECTION  (every way of asking)
# ---------------------------------------------------------------------------
# Distinguishes "what is X" from "why is X important" from "features of X"
# etc., so the SAME topic can give a genuinely different answer depending
# on what was actually asked. Patterns are checked in order; first hit wins.

QUESTION_TYPES = ("definition", "importance", "features", "causes", "effects",
                  "examples", "process", "fact", "general")

_TYPE_PATTERNS = [
    # ---- importance / role / need / purpose / benefit
    (re.compile(r"\bwhy\s+(is|are|was|were)\b.*\b(important|needed|necessary|useful|essential|significant|crucial)\b", re.I), "importance"),
    (re.compile(r"\bwhy\s+(do|does|did|should|must)\b.*\b(matter|need|study|learn|require)\b", re.I), "importance"),
    (re.compile(r"\b(importance|significance|role|need|purpose|value|benefits?|advantages?|uses?|relevance|necessity)\s+of\b", re.I), "importance"),
    (re.compile(r"\bhow\s+(is|are|does|do)\b.*\b(useful|help|helpful|benefit)\b", re.I), "importance"),
    (re.compile(r"\b(mahatva|mahatv|kyu\s+(zaroori|important|jaruri)|kyun\s+(zaroori|important|jaruri)|zaroorat)\b", re.I), "importance"),
    (re.compile(r"\b(importance|significance)\s*$", re.I), "importance"),
    # ---- features / characteristics / principles / parts / classification
    (re.compile(r"\b(main|key|salient|chief|major|important|basic|essential)?\s*(features?|characteristics?|principles?|elements?|components?|pillars?|limbs?|parts?|functions?|classification|categories|stages)\s+of\b", re.I), "features"),
    (re.compile(r"\bwhat\s+are\s+the\b.*\b(features?|characteristics?|principles?|elements?|components?|pillars?|functions?)\b", re.I), "features"),
    (re.compile(r"\b(visheshta|visheshtayein|visheshtaen|khasiyat|lakshan)\b", re.I), "features"),
    (re.compile(r"\b(features?|characteristics?|principles?)\s*$", re.I), "features"),
    # ---- causes / reasons / origin
    (re.compile(r"\b(causes?|reasons?|factors?|origin|origins)\s+(of|for|behind|responsible|affecting|of\s+the)\b", re.I), "causes"),
    (re.compile(r"\bwhat\s+(cause|causes|caused|led\s+to|leads\s+to|triggers?|triggered)\b", re.I), "causes"),
    (re.compile(r"\bwhy\s+(does|do|did|is|are|was|were)\b.*\b(happen|occur|occurs|arise|arises|form|forms|start|started|begin|began|take\s+place)\b", re.I), "causes"),
    (re.compile(r"\bhow\s+(does|do|did)\b.*\b(occur|occurs|start|begin|began|arise|come\s+about)\b", re.I), "causes"),
    (re.compile(r"\bhow\s+is\b.*\bcaused\b", re.I), "causes"),
    (re.compile(r"\b(karan|kaaran|wajah|kyu\s+hota|kyun\s+hota|kyu\s+hua|kyun\s+hua)\b", re.I), "causes"),
    (re.compile(r"\b(causes?|reasons?)\s*$", re.I), "causes"),
    # ---- effects / impact / consequences
    (re.compile(r"\b(effects?|impacts?|consequences?|results?|outcomes?|influence|implications?)\s+(of|on)\b", re.I), "effects"),
    (re.compile(r"\bhow\s+(does|do|did|will|can)\b.*\b(affect|influence|impact|change)\b", re.I), "effects"),
    (re.compile(r"\bwhat\s+(happens?|happened|changes?)\b.*\b(because|after|due\s+to|when)\b", re.I), "effects"),
    (re.compile(r"\b(prabhav|asar|parinam|nateeja|natija)\b", re.I), "effects"),
    (re.compile(r"\b(effects?|impacts?|consequences?)\s*$", re.I), "effects"),
    # ---- examples / case studies
    (re.compile(r"\b(examples?|instances?|illustrations?|case\s+stud(y|ies))\s+(of|on|for|to)\b", re.I), "examples"),
    (re.compile(r"\b(with|give|giving)\s+(an?\s+)?(real[\s-]life\s+)?examples?\b", re.I), "examples"),
    (re.compile(r"\billustrate\b", re.I), "examples"),
    (re.compile(r"\b(udaharan|udahran|misal)\b", re.I), "examples"),
    (re.compile(r"\bexamples?\s*$", re.I), "examples"),
    # ---- process / working / steps
    (re.compile(r"\bhow\s+(does|do|is|are|did|can|to|it)\b", re.I), "process"),
    (re.compile(r"\b(process|working|mechanism|steps?|procedure|method)\s+(of|in|for)\b", re.I), "process"),
    (re.compile(r"\bkaise\b", re.I), "process"),
    # ---- direct facts: who / when / where / which / how many / name / state
    (re.compile(r"^\s*(who|whom|whose|when|where|which|how\s+many|how\s+much|how\s+long|how\s+old)\b", re.I), "fact"),
    (re.compile(r"^\s*(name|state|mention|give\s+(one|some|a)\s+facts?|facts?\s+(about|on)|tell\s+me\s+a\s+fact|fun\s+facts?|one\s+fact)\b", re.I), "fact"),
    (re.compile(r"\b(facts?)\s+(about|on|of)\b", re.I), "fact"),
    # ---- definition / meaning
    (re.compile(r"^\s*what\s+is\b", re.I), "definition"),
    (re.compile(r"^\s*what\s+are\b", re.I), "definition"),
    (re.compile(r"^\s*whats?\b", re.I), "definition"),
    (re.compile(r"^\s*define\b", re.I), "definition"),
    (re.compile(r"\b(meaning|definition)\b", re.I), "definition"),
    (re.compile(r"\bwhat\s+do\s+you\s+mean\s+by\b", re.I), "definition"),
    (re.compile(r"\bwhat\s+(is|does)\b.*\bmean\b", re.I), "definition"),
    (re.compile(r"\b(explain|understand|know)\s+the\s+(term|concept|meaning)\b", re.I), "definition"),
    (re.compile(r"\b(kya\s+hai|kya\s+hota\s+hai|kya\s+hoti\s+hai|matlab|arth|paribhasha)\b", re.I), "definition"),
]


def _detect_question_type(raw: str) -> str:
    for pattern, qtype in _TYPE_PATTERNS:
        if pattern.search(raw):
            return qtype
    return "general"


# ---------------------------------------------------------------------------
# 5. TOPIC-PHRASE EXTRACTION  +  TOPIC MATCHING
# ---------------------------------------------------------------------------

# Pure wrapper words: stripped even if they also occur in the KB's own
# vocabulary (they never carry the subject of a question).
_ALWAYS_STRIP = {
    "question", "questions", "ques", "answer", "answers", "ans", "exam",
    "class", "ncert", "cbse", "sst", "thanks", "thank", "urgent", "fast",
    "today", "tomorrow", "asap", "tonight", "sir", "madam", "mam", "bhai",
    "dear", "ai", "hey", "hello", "hi", "hii", "kindly", "doubt",
    "word", "words", "simple", "simply", "easy", "easily", "language",
    "point", "points", "bullet", "bullets", "line", "lines", "sentence",
    "nutshell", "operate", "operates", "make", "makes", "like", "step",
    "steps", "understand", "teach", "learn",
    # words that only say HOW the question is phrased (importance / cause /
    # effect / process styles), never WHICH topic it is about
    "salient", "study", "should", "needed", "useful", "helpful", "necessary",
    "essential", "crucial", "matter", "matters", "happen", "happens",
    "happened", "occur", "occurs", "occurred", "work", "works", "working",
    "formed", "done", "start", "started", "begin", "began", "develop",
    "developed", "affect", "affects", "influence", "help", "helps", "bring",
    "responsible", "behind", "affecting",
    "one", "two", "three", "four", "five", "six", "seven", "eight", "ten",
}

# Multi-word wrappers removed as whole phrases BEFORE tokenising, so that
# e.g. "i need to know" is dropped without touching "needs and wants".
_WRAPPER_PHRASES_RE = re.compile(
    r"\b(?:i|we)\s+(?:really\s+)?(?:need|want|wanna|would\s+like|have)\s+to\s+(?:know|learn|understand|study|revise)\b|"
    r"\b(?:i|we)\s+(?:need|want|wanna)\b|\bneed\s+to\s+know\b|"
    r"\b(?:can|could|would|will)\s+(?:you|u)(?:\s+please)?\b|"
    r"\blet\s+me\s+know\b|\btell\s+me\b|\bone\s+more\s+question\b|"
    r"\bquick\s+question\b|\bmy\s+doubt\s+is\b|\bi\s+have\s+a\s+(?:doubt|question)\b|"
    r"\bfor\s+(?:the\s+)?(?:exam|test|class\s+9|board)\b|\bok\s+so\b|\bexam\s+tomorrow\b|"
    r"\bbefore\s+(?:the\s+)?exam\b|\bstate\s+(?:the|any|some|a|an|one)\b|"
    r"\b(?:key|main|different|various|important)\s+(?:points?|features?|characteristics?|principles?|parts?|elements?|components?)\b")


def _extract_topic_phrase(raw: str) -> str:
    """Strip stop-words / filler / mode-words / question-type words,
    leaving (as best as possible) just the subject the student is
    actually asking about. Filler words are only dropped if they are not
    themselves part of the KB's own vocabulary."""
    norm = _WRAPPER_PHRASES_RE.sub(" ", _normalise(raw))
    tokens = norm.split()
    kept = []
    for t in tokens:
        f = _fix_spelling(t)
        if t in _STOPWORDS or f in _STOPWORDS or t in _ALWAYS_STRIP or t.isdigit():
            continue
        if (t in _FILLER or f in _FILLER) and _singularise(f) not in _ALL_TOPIC_WORDS \
                and f not in _ALL_TOPIC_WORDS:
            continue
        kept.append(f)
    phrase = " ".join(kept).strip()
    return phrase if phrase else _normalise(raw)


_MATCH_THRESHOLD = 0.55         # min weighted fraction of query tokens that must match
_FUZZY_TOKEN_THRESHOLD = 0.84   # min per-token similarity to count as a typo-match
_FUZZY_HIT_WEIGHT = 0.7         # a fuzzy hit counts for less than an exact hit


@functools.lru_cache(maxsize=None)
def _fuzzy_matches(token: str) -> frozenset:
    """All KB vocabulary words that a (>=5 letter) token is a strict
    typo-match of. Cached per token — this is what keeps matching fast
    even across 100,000+ question phrasings."""
    sm = difflib.SequenceMatcher(None)
    sm.set_seq1(token)
    out = set()
    for w in _ALL_TOPIC_WORDS:
        sm.set_seq2(w)
        if (sm.real_quick_ratio() >= _FUZZY_TOKEN_THRESHOLD
                and sm.quick_ratio() >= _FUZZY_TOKEN_THRESHOLD
                and sm.ratio() >= _FUZZY_TOKEN_THRESHOLD):
            out.add(w)
    return frozenset(out)


def _token_score(query_tokens: set[str], topic_tokens: set[str]) -> float:
    """Weighted fraction of the QUERY's meaningful tokens that are found in
    the topic's token set — an exact hit counts fully, a strict per-word
    typo-tolerant ("fuzzy") hit counts for less. Short tokens (<5 chars)
    must match exactly, and the discounted fuzzy weight stops a single
    coincidental near-miss word from matching an unrelated topic."""
    if not query_tokens or not topic_tokens:
        return 0.0
    hits = 0.0
    for qt in query_tokens:
        if qt in topic_tokens:
            hits += 1.0
            continue
        if len(qt) >= 5 and (_fuzzy_matches(qt) & topic_tokens):
            hits += _FUZZY_HIT_WEIGHT
    return hits / len(query_tokens)


# Stage-1 index: every alias in TWO forms — as written, and with the same
# stop-word/filler stripping a query gets — so "branches of social science"
# matches a query that has had its "of" removed. Built once at import time.
_STAGE1: list[tuple[str, str, bool]] = []
for _key in KB:
    _titles = _CHAPTER_TITLE_ALIASES.get(_key, set())
    _seen_forms: set[str] = set()
    for _c in _TOPIC_PHRASES[_key]:
        _cn = _normalise(_c)
        _is_title = _cn in _titles
        for _form in (_cn, _normalise(_extract_topic_phrase(_c))):
            if _form and _form not in _seen_forms:
                _seen_forms.add(_form)
                _STAGE1.append((_key, _form, _is_title))


def _find_topic_stage1(query: str) -> str | None:
    """Confident matches only: the (stripped) query equals, contains, or is
    contained in a real topic name/alias."""
    phrase = _extract_topic_phrase(query)
    if not phrase:
        return None
    norm_phrase = _normalise(phrase)
    padded = f" {norm_phrase} "
    best_key, best_len = None, 0
    for key, form, is_title in _STAGE1:
        if form == norm_phrase:
            return key      # perfect match — stop immediately
        if is_title or len(form) < 4:
            continue        # bare chapter title / too generic: exact only
        if f" {form} " in padded or padded in f" {form} ":
            if len(form) > best_len:
                best_key, best_len = key, len(form)
    return best_key


def find_topic(query: str) -> str | None:
    """Match free text against KB topics. Returns a topic key, or None if
    nothing is a confident enough match (the engine never guesses wildly).

    Stage 1: exact / whole-word phrase match against the topic's key or a
             real alias (longest match wins).
    Stage 2: token-overlap scoring — what fraction of the query's own
             meaningful words are found (exactly, or via a strict per-word
             typo-tolerant match) among that topic's alias/keyword words;
             ties are broken in favour of the topic whose own name/aliases
             share the most words with the query.
    """
    hit = _find_topic_stage1(query)
    if hit:
        return hit

    phrase = _extract_topic_phrase(query)
    query_tokens = _tokenise(phrase) if phrase else set()
    if not query_tokens:
        return None

    best_key, best_score = None, 0.0
    for key, topic_tokens in _TOPIC_TOKENS.items():
        score = _token_score(query_tokens, topic_tokens)
        score += 0.01 * len(query_tokens & _TOPIC_CORE_TOKENS[key]) / len(query_tokens)
        if score > best_score:
            best_score, best_key = score, key

    return best_key if best_score >= _MATCH_THRESHOLD else None


# "role of X", "principles of X", "factors responsible for X" ... the words
# before "of" say WHAT is being asked, X says WHICH topic. Looking at X on
# its own stops e.g. "principles of elections" being pulled to democracy.
_LEAD_RE = re.compile(
    r"\b(?:role|importance|significance|purpose|need|value|benefits?|"
    r"advantages?|uses?|relevance|principles?|features?|characteristics?|"
    r"elements?|components?|functions?|causes?|reasons?|"
    r"factors?(?:\s+responsible)?|effects?|impacts?|consequences?|results?|"
    r"examples?|origin|working|process|meaning|definition)\s+(?:of|for|behind|on)\b",
    re.IGNORECASE)


def _find_topic_smart(text: str) -> str | None:
    plain = find_topic(text)
    stripped = _LEAD_RE.sub(" ", text)
    if stripped != text:
        confident = _find_topic_stage1(stripped)
        if confident:
            return confident
    return plain


def search_topics(query: str, limit: int = 5) -> list[tuple[str, float]]:
    """Return up to `limit` (topic_key, score) candidates for a query,
    best first — useful for debugging / autosuggest / fallback hints."""
    phrase = _extract_topic_phrase(query)
    query_tokens = _tokenise(phrase)
    scored = [(key, _token_score(query_tokens, toks)) for key, toks in _TOPIC_TOKENS.items()]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:limit]


def list_topics() -> list[str]:
    """Return all topic keys grouped implicitly by chapter order."""
    return list(KB.keys())


# ---------------------------------------------------------------------------
# 6. FIELD SELECTION  (question type -> KB field, with graceful fallback)
# ---------------------------------------------------------------------------

def _format_field(value) -> str:
    if isinstance(value, list):
        return "\n".join(f"• {item}" for item in value)
    return value


def _select_field(entry: dict, mode: str | None, qtype: str) -> str:
    """Pick the best field for this entry given an explicit mode (if any)
    and the detected question type. Falls back to real content already in
    the entry rather than ever inventing something new."""

    # An explicit mode (from a "short:"/"long:" prefix, "N marks", or a
    # clear natural-language request) always wins: the student asked for a
    # LENGTH/FORMAT, not a category.
    if mode:
        if mode == "definition":
            return _format_field(entry.get("definition", entry["medium"]))
        return _format_field(entry.get(mode, entry["medium"]))

    if qtype == "definition":
        return _format_field(entry.get("definition", entry["short"]))

    if qtype == "importance":
        if "importance" in entry:
            return _format_field(entry["importance"])
        return _format_field(entry.get("long", entry["medium"]))

    if qtype == "features":
        if "features" in entry:
            return _format_field(entry["features"])
        return _format_field(entry.get("short_note", entry["medium"]))

    if qtype == "causes":
        if "causes" in entry:
            return _format_field(entry["causes"])
        return _format_field(entry.get("long", entry["medium"]))

    if qtype == "effects":
        if "effects" in entry:
            return _format_field(entry["effects"])
        return _format_field(entry.get("long", entry["medium"]))

    if qtype in ("examples", "process"):
        # examples and step-by-step working live in the detailed answer
        return _format_field(entry.get("long", entry["medium"]))

    if qtype == "fact":
        # who / when / where / which / how many -> the crisp answer
        return _format_field(entry.get("short", entry["medium"]))

    return _format_field(entry[DEFAULT_MODE])


# ---------------------------------------------------------------------------
# 7. FALLBACK
# ---------------------------------------------------------------------------

FALLBACK_MESSAGE = (
    "I couldn't confidently identify that topic from my current Class 9 "
    "SST knowledge bank. Try asking about a chapter, concept, definition, "
    "event, process, place, or person from the NCERT syllabus."
)


def _fallback_with_suggestions(query: str) -> str:
    suggestions = search_topics(query, limit=3)
    lines = [FALLBACK_MESSAGE]
    real_suggestions = [key for key, score in suggestions if score > 0.12]
    if real_suggestions:
        lines.append("")
        lines.append("You could try asking, for example:")
        for key in real_suggestions:
            lines.append(f"  • \"what is {topic_label(key).lower()}?\"")
    lines.append("")
    lines.append(
        "Say \"help\" to see how to ask, or \"topics\" to see everything "
        "I can explain. (Currently covers parts of NCERT Grade 9 "
        "Chapters 1-9 — not the full syllabus.)"
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 8. CONVERSATION LAYER  (greetings, thanks, help, identity, etc.)
# ---------------------------------------------------------------------------

_GREET_PREFIX_RE = re.compile(
    r"^\s*(?:hi+|hello+|hey+|heyy+|hii+|hola|yo|namaste|namaskar|salaam|"
    r"good\s+(?:morning|afternoon|evening|night)|sir|madam|mam|ma'am|bhai|"
    r"dear|please|pls|plz|kindly|excuse\s+me|sst\s+ai|sahil\s+ai)\b[\s,!.:;-]*",
    re.IGNORECASE)


def _strip_greeting_prefix(text: str) -> str:
    """Remove leading 'hi', 'hello sir', 'good morning' etc. so that
    'hello sir what is democracy' is answered as 'what is democracy'."""
    prev = None
    while prev != text:
        prev = text
        text = _GREET_PREFIX_RE.sub("", text, count=1)
    return text.strip()


# (key, compiled regex on the NORMALISED text, "full" | "search")
_SMALLTALK = [
    ("creator", re.compile(r"\bwho\s+(created|made|built|developed|designed|programmed|wrote|trained)\s+(you|sst\s+ai|this|this\s+bot|this\s+app|this\s+ai)\b|\bwho\s+is\s+your\s+(creator|developer|maker|owner|father)\b|\b(your|the)\s+(creator|developer)\b|^who\s+is\s+sahil$|^(tell\s+me\s+)?about\s+sahil$|^(which|what)\s+(school|class)(\s+is\s+this)?$|^(creator|sahil)\s+s?\s*(school|class)|^school\s+name$"), "search"),
    ("robot", re.compile(r"^(are|r)\s+(you|u)\s+(a\s+|an\s+)?(robot|bot|ai|human|real|person|chatgpt|gpt|alexa|siri|gemini|claude|machine)$|^(are|r)\s+(you|u)\s+(a\s+)?(real\s+)?(human|person|robot|bot)\b"), "search"),
    ("name", re.compile(r"^(what\s+is\s+your\s+name|whats?\s+your\s+name|what\s+s\s+your\s+name|your\s+name|tell\s+me\s+your\s+name|tumhara\s+naam(\s+kya\s+hai)?|aapka\s+naam(\s+kya\s+hai)?|naam\s+kya\s+hai(\s+tumhara)?|who\s+am\s+i\s+talking\s+to)$"), "full"),
    ("who", re.compile(r"^(who\s+are\s+you|what\s+are\s+you|who\s+r\s+u|tell\s+me\s+about\s+yourself|introduce\s+yourself|about\s+you|about\s+yourself|what\s+is\s+sst\s+ai|whats?\s+sst\s+ai|tell\s+me\s+about\s+sst\s+ai|about\s+sst\s+ai|who\s+is\s+sst\s+ai)$"), "full"),
    ("capability", re.compile(r"^(what\s+can\s+(you|u)\s+do|what\s+do\s+you\s+do|how\s+can\s+you\s+help(\s+me)?|your\s+features|what\s+are\s+your\s+features|capabilities|what\s+can\s+you\s+help\s+(me\s+)?with|what\s+all\s+can\s+you\s+do|what\s+can\s+you\s+teach(\s+me)?)$"), "full"),
    ("howareyou", re.compile(r"^(how\s+are\s+(you|u)(\s+doing|\s+today)?|how\s+r\s+u|how\s+do\s+you\s+do|what\s+s\s+up|whats\s+up|wassup|sup|kaise\s+ho(\s+aap)?|kya\s+haal(\s+hai)?|how\s+is\s+it\s+going|how\s+s\s+it\s+going|you\s+okay|are\s+you\s+(fine|ok|okay))$"), "full"),
    ("thanks", re.compile(r"^(thanks?|thank\s+(you|u)|thx|ty|tysm|shukriya|dhanyawad|dhanyavaad|much\s+appreciated|appreciate\s+it|great\s+help)(\s+(a\s+lot|a\s+ton|so\s+much|very\s+much|bro|sir|mam|madam|for\s+the\s+help|for\s+helping(\s+me)?|for\s+that|again))*$"), "full"),
    ("bye", re.compile(r"^(bye+|bye\s+bye|goodbye|good\s+bye|see\s+(you|ya)(\s+(later|soon|tomorrow))?|tata|ta\s+ta|alvida|good\s+night|gn|take\s+care|talk\s+to\s+you\s+later|ttyl|cya|i\s+(am|m)\s+(leaving|going)|i\s+have\s+to\s+go|gotta\s+go)$"), "full"),
    ("sorry", re.compile(r"^(sorry|my\s+bad|oops|apologies|maaf\s+(karo|kijiye|kijiyega))$"), "full"),
    ("compliment", re.compile(r"^(you\s+(are|re)\s+(so\s+|very\s+)?(smart|good|great|awesome|amazing|helpful|best|nice|clever|intelligent)|good\s+bot|nice\s+bot|well\s+done|good\s+job|great\s+job|nice\s+work|love\s+you|i\s+like\s+you|best\s+ai|best\s+bot|you\s+are\s+the\s+best)$"), "full"),
    ("confused", re.compile(r"^(i\s+(do\s+not|dont|don\s+t|didn\s+t|did\s+not)\s+(understand|get\s+it|get\s+this|know)|i\s+(am|m)\s+confused|im\s+confused|confused|not\s+clear|unclear|samajh\s+nahi\s+(aaya|aya)|nahi\s+samjha|nahi\s+samjhi|explain\s+again|again|say\s+again|repeat|explain\s+more|more|more\s+details|tell\s+me\s+more|simplify|make\s+it\s+simple|explain\s+simply|too\s+difficult|too\s+hard|this\s+is\s+hard|it\s+s\s+difficult|difficult)$"), "full"),
    ("ack", re.compile(r"^(ok(ay)?|k|kk|cool|nice|great|good|awesome|fine|alright|all\s+right|got\s+it|understood|i\s+understand|i\s+see|makes\s+sense|sure|yes|yeah|yep|yup|hmm+|hm+|oh|oh\s+ok(ay)?|ohh+|wow|perfect|excellent|super|superb|accha|acha|theek\s+hai|thik\s+hai|samajh\s+gaya|samajh\s+gayi|no|nope|nothing)$"), "full"),
    ("help", re.compile(r"^(help(\s+me)?|i\s+need\s+help|need\s+help|menu|options|commands|how\s+to\s+use(\s+you|\s+this)?|how\s+do\s+i\s+use\s+you|how\s+does\s+this\s+work|what\s+should\s+i\s+ask|what\s+can\s+i\s+ask|guide|instructions|usage|user\s+guide|how\s+to\s+ask)$"), "full"),
    ("topics", re.compile(r"^(topics|list\s+(of\s+)?topics|show\s+topics|all\s+topics|what\s+topics(\s+do\s+you\s+(know|cover))?(\s+are\s+covered)?|syllabus|show\s+syllabus|chapters|list\s+(of\s+)?chapters|all\s+chapters|show\s+chapters|chapter\s+list|what\s+chapters(\s+do\s+you\s+cover)?|contents|table\s+of\s+contents|what\s+do\s+you\s+(know|cover)|which\s+(topics|chapters))$"), "full"),
    ("tips", re.compile(r"\b(tips?|advice|strategy|tricks?)\b.*\b(sst|social\s+(science|studies)|exams?|stud(y|ying)|preparation|score|marks)\b|\bhow\s+to\s+(study|learn|prepare|score|remember|revise|write)\b.*\b(sst|social|exams?|answers?)\b|^(study|exam)\s+tips$"), "search"),
    ("greeting", re.compile(r"^(hi+|hello+|hey+|heyy+|hii+|hola|yo|namaste|namaskar|salaam|good\s+(morning|afternoon|evening)|hello\s+there|hi\s+there|hey\s+there|greetings|(hi|hello|hey)\s+sst\s+ai)$"), "full"),
]


def _match_smalltalk(text: str) -> str | None:
    norm = _normalise(text)
    if not norm or len(norm.split()) > 12:
        return None
    for key, rx, kind in _SMALLTALK:
        if (rx.fullmatch(norm) if kind == "full" else rx.search(norm)):
            return key
    return None


def _pick(options: list[str], seed: str) -> str:
    return options[sum(ord(c) for c in seed) % len(options)]


def _help_text() -> str:
    return (
        "I am SST AI — your Class 9 Social Science tutor (NCERT, 2026-27). "
        "Here is how to ask me:\n\n"
        "• Ask normally: \"what is democracy?\", \"why are elections important?\", "
        "\"causes of the Emergency\", \"features of democracy\".\n"
        "• Pick the answer length: start with \"short:\", \"medium:\", \"long:\", "
        "\"short note:\" or \"definition:\" — e.g. \"short note: monsoon\".\n"
        "• Or say it naturally: \"in one line\", \"in detail\", \"in points\", "
        "\"in simple words\", \"for 3 marks\", \"5 marks answer\".\n"
        "• Compare: \"difference between weather and climate\", "
        "\"monsoon vs atmosphere\".\n"
        "• Practice: \"quiz me on elections\", \"important questions on "
        "opportunity cost\".\n"
        "• Hinglish works too: \"democracy kya hai\", \"monsoon ka mahatva\".\n"
        "• Say \"topics\" to see everything I cover."
    )


def _topics_text() -> str:
    by_chapter: dict[str, list[str]] = {}
    for key, e in KB.items():
        by_chapter.setdefault(e.get("chapter", "Other"), []).append(topic_label(key))
    lines = ["Here is what I can explain right now (NCERT Class 9 SST, Part 1):", ""]
    for ch in PROJECT_INFO["chapters"]:
        if ch in by_chapter:
            lines.append(f"{ch}")
            for lbl in by_chapter[ch]:
                lines.append(f"   • {lbl}")
    lines.append("")
    lines.append("Ask about any of these — for example \"short note on "
                 "plate tectonics\" or \"why is monsoon important?\".")
    return "\n".join(lines)


def _smalltalk_reply(key: str, text: str) -> str:
    seed = text or key
    n = _normalise(text)
    if key == "greeting":
        opening = ""
        for part, word in (("morning", "Good morning! "), ("afternoon", "Good afternoon! "),
                           ("evening", "Good evening! ")):
            if part in n:
                opening = word
        if opening:
            return (opening + "I'm SST AI, your Class 9 Social Science tutor. What "
                    "would you like to learn today? Try \"what is democracy?\" or say "
                    "\"help\".")
        return _pick([
            "Hello! I am SST AI, your Class 9 Social Science tutor. Ask me anything "
            "from History, Geography, Political Science or Economics — for example "
            "\"what is democracy?\" or \"short note on monsoon\".",
            "Hi there! I'm SST AI. Which NCERT Class 9 SST topic shall we study "
            "today? Try \"explain plate tectonics\" or \"why are elections important?\".",
            "Namaste! SST AI here, ready to help with Class 9 Social Science. "
            "Type a topic or question, or say \"help\" to see everything I can do.",
        ], seed + str(len(seed)))
    if key == "howareyou":
        return _pick([
            "I'm doing great, thank you for asking! Ready to help with your Class 9 "
            "SST. What would you like to learn today?",
            "All good here! Which chapter are we tackling — History, Geography, "
            "Political Science or Economics?",
        ], seed)
    if key == "thanks":
        return _pick([
            "You're welcome! Keep asking — every doubt cleared is a mark earned.",
            "Happy to help! Want to test yourself? Say \"quiz me on <topic>\".",
            "Glad that helped! Ask me another question anytime.",
        ], seed)
    if key == "bye":
        return _pick([
            "Goodbye! All the best for your studies and exams.",
            "See you soon! Keep revising regularly — small steps every day.",
        ], seed)
    if key == "sorry":
        return "No problem at all! What would you like to ask?"
    if key == "compliment":
        return "Thank you, that's kind of you! Let's keep learning — which topic next?"
    if key == "ack":
        return _pick([
            "Great! Ask me another question, or say \"quiz me on <topic>\" to test yourself.",
            "Okay! What would you like to study next?",
        ], seed)
    if key == "confused":
        return ("No problem — let's make it simpler. Tell me the topic and add "
                "\"in simple words\" (e.g. \"explain democracy in simple words\"), "
                "or use \"short:\" for a quick answer and \"long:\" for a full "
                "explanation.")
    if key == "help":
        return _help_text()
    if key == "topics":
        return _topics_text()
    if key == "name":
        return "My name is SST AI — a Class 9 Social Science tutor created by Sahil."
    if key == "who":
        return ("I am SST AI, a Class 9 Social Science tutor for the NCERT book "
                "'Understanding Society: India and Beyond' (Part 1). I cover History, "
                "Geography, Political Science and Economics, and I was created by "
                "Sahil (Class 9, Daffodils Public School).")
    if key == "creator":
        return ("I was created by Sahil, a Class 9 student of Daffodils Public "
                "School, for the 2026-27 academic year — the project is called "
                "SST AI, a Class 9 Social Science AI Tutor.")
    if key == "capability":
        return ("I can explain Class 9 Social Science topics from History, "
                "Geography, Political Science and Economics. I give short "
                "answers, medium explanations, detailed answers, definitions, "
                "short notes, causes, effects, features, importance and examples; "
                "I can compare two topics, quiz you, and understand greetings, "
                "Hinglish and typos. Say \"help\" to see how to ask.")
    if key == "robot":
        return ("I'm SST AI — a computer program, not a human. Sahil built me as a "
                "Class 9 Social Science tutor that answers from a knowledge bank "
                "based on the NCERT textbook, so I only cover this syllabus.")
    if key == "tips":
        return ("General study tips for SST (these are common study advice, not "
                "from the textbook):\n"
                "• Read the NCERT chapter first, then make your own short notes.\n"
                "• Learn key terms with their definitions — they fetch easy marks.\n"
                "• Practise map work and timelines regularly.\n"
                "• Write answers in points for 3–5 mark questions.\n"
                "• Test yourself: say \"quiz me on <topic>\" and check your answers.")
    return _help_text()


# ---------------------------------------------------------------------------
# 9. COMPARISON QUESTIONS  ("difference between X and Y", "X vs Y" ...)
# ---------------------------------------------------------------------------

_COMPARE_PATTERNS = [
    re.compile(r"^(?:(?:what\s+(?:is|are)|explain|state|write|give|tell\s+me|list)\s+the\s+)?(?:difference|differences|distinction|similarit(?:y|ies)|contrast)\s+(?:between|of|b/w|bw)\s+(?P<a>.+?)\s+(?:and|&|vs\.?|versus|with|from|n)\s+(?P<b>.+)$", re.I),
    re.compile(r"^(?:please\s+)?(?:compare|contrast|differentiate|distinguish)\s+(?:between\s+)?(?P<a>.+?)\s+(?:and|&|vs\.?|versus|with|from|to|n)\s+(?P<b>.+)$", re.I),
    re.compile(r"^how\s+(?:is|are|does|do)\s+(?P<a>.+?)\s+(?:different|differ)\s+from\s+(?P<b>.+)$", re.I),
    re.compile(r"^(?P<a>.+?)\s+(?:vs\.?|versus)\s+(?P<b>.+)$", re.I),
    re.compile(r"^(?P<a>.+?)\s+(?:and|aur|n)\s+(?P<b>.+?)\s+(?:mein\s+|me\s+|ka\s+|ke\s+)?(?:difference|differences|antar|fark|comparison)$", re.I),
]


def _try_compare(text: str, mode: str | None):
    t = text.strip().rstrip("?.! ")
    for rx in _COMPARE_PATTERNS:
        m = rx.match(t)
        if not m:
            continue
        ta, tb = find_topic(m.group("a")), find_topic(m.group("b"))
        if ta and tb:
            return ta, tb
    return None


def _compare_answer(ta: str, tb: str, mode: str | None) -> str:
    if ta == tb:
        # both sides live inside one topic (e.g. weather vs climate,
        # direct vs representative democracy): its notes already contrast them
        e = KB[ta]
        field = mode if mode in ("short", "medium", "long", "short_note") else "short_note"
        return _format_field(e.get(field, e["medium"]))
    ea, eb = KB[ta], KB[tb]
    la, lb = topic_label(ta), topic_label(tb)
    if mode in ("short", "definition"):
        f = "definition" if mode == "definition" else "short"
        return f"{la}: {_format_field(ea.get(f, ea['short']))}\n\n{lb}: {_format_field(eb.get(f, eb['short']))}"
    body_field = "medium" if mode in ("long", "medium") else "short_note"
    return (
        f"Comparison: {la} vs {lb}\n\n"
        f"■ {la}  ({ea.get('chapter', '')})\n"
        f"Meaning: {_format_field(ea.get('definition', ea['short']))}\n"
        f"{_format_field(ea.get(body_field, ea['medium']))}\n\n"
        f"■ {lb}  ({eb.get('chapter', '')})\n"
        f"Meaning: {_format_field(eb.get('definition', eb['short']))}\n"
        f"{_format_field(eb.get(body_field, eb['medium']))}\n\n"
        "Exam tip: present this as a two-column table (Basis | "
        f"{la} | {lb}) for full marks."
    )


# ---------------------------------------------------------------------------
# 10. PRACTICE QUESTIONS  ("quiz me on X", "important questions on X")
# ---------------------------------------------------------------------------

_QUIZ_RE = re.compile(
    r"^(?:quiz(?:\s+me)?|test\s+me|ask\s+me(?:\s+(?:some\s+|a\s+few\s+)?questions?)?|"
    r"practice\s+questions?|give\s+me\s+(?:some\s+|a\s+few\s+|\d+\s+)?(?:practice\s+|important\s+|expected\s+|exam\s+|mcq\s+)?questions?|"
    r"(?:important|expected|exam|practice)\s+questions?|mcqs?)"
    r"\s*(?:on|about|of|for|from|in)?\s*(?P<t>.*)$", re.I)


def practice_questions(key: str) -> list[str]:
    """Exam-style practice questions for a topic, each of which this
    engine can answer (so a student can paste it straight back in)."""
    e, lbl = KB[key], topic_label(key)
    qs = [f"Define {lbl}. (1 mark)"]
    if "importance" in e:
        qs.append(f"Why is {lbl} important? (3 marks)")
    if "features" in e:
        qs.append(f"State the main features of {lbl}. (3 marks)")
    if "causes" in e:
        qs.append(f"What are the causes of {lbl}? (3 marks)")
    if "effects" in e:
        qs.append(f"Explain the effects of {lbl}. (3 marks)")
    qs.append(f"Write a short note on {lbl}. (3 marks)")
    qs.append(f"Explain {lbl} in detail. (5 marks)")
    return qs


def _try_quiz(text: str) -> str | None:
    m = _QUIZ_RE.match(text.strip().rstrip("?.! "))
    if not m:
        return None
    subject = m.group("t").strip()
    key = find_topic(subject) if subject else None
    if not key:
        return ("Tell me the topic you want to practise — for example "
                "\"quiz me on elections\" or \"important questions on monsoon\".")
    lines = [f"Practice questions — {topic_label(key)} ({KB[key].get('chapter', '')}):", ""]
    lines += [f"{i}. {q}" for i, q in enumerate(practice_questions(key), 1)]
    lines += ["", "Type any of these questions and I'll give you the answer."]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 11. PUBLIC API
# ---------------------------------------------------------------------------

def parse_query(raw: str) -> tuple[str | None, str, str]:
    """Returns (explicit_mode_or_None, question_type, topic_query_text)."""
    mode, rest = _detect_mode(raw)
    qtype = _detect_question_type(rest)
    return mode, qtype, rest


def resolve(query: str, mode: str | None = None) -> dict:
    """Work out what a query is: small talk, a quiz request, a comparison,
    a topic question, or something unknown. Returns a dict with 'kind',
    plus 'topic'/'mode'/'qtype'/'text' where relevant. answer() renders it;
    self_test() uses it to check the 100,000+ question bank."""
    text = _strip_greeting_prefix(str(query or "").strip())
    if not text:
        return {"kind": "smalltalk", "key": "greeting", "text": str(query or "")}

    st = _match_smalltalk(text)
    if st:
        return {"kind": "smalltalk", "key": st, "text": text}

    if _QUIZ_RE.match(text.strip().rstrip("?.! ")):
        quiz = _try_quiz(text)
        subject = _QUIZ_RE.match(text.strip().rstrip("?.! ")).group("t").strip()
        return {"kind": "quiz", "topic": find_topic(subject) if subject else None,
                "text": text, "reply": quiz}

    explicit_mode, qtype, topic_text = parse_query(text)
    final_mode = mode or explicit_mode

    pair = _try_compare(topic_text, final_mode)
    if pair:
        return {"kind": "compare", "topic": pair[0], "topic_b": pair[1],
                "mode": final_mode, "text": text}

    key = _find_topic_smart(topic_text) or _find_topic_smart(text)

    if key is None:
        cleaned_topic = topic_text
        for word in ["basic", "features", "feature", "classification", "types"]:
            cleaned_topic = cleaned_topic.replace(word, "")
        key = _find_topic_smart(cleaned_topic)

    if key is None:
        return {"kind": "fallback", "text": text}

    return {"kind": "topic", "topic": key, "mode": final_mode,
            "qtype": qtype, "text": text}


def _core_answer(query: str, mode: str | None) -> str:
    """The actual answer-building pipeline, without any caching."""
    r = resolve(query, mode)
    kind = r["kind"]
    if kind == "smalltalk":
        return _smalltalk_reply(r["key"], r["text"])
    if kind == "quiz":
        return r["reply"]
    if kind == "compare":
        return _compare_answer(r["topic"], r["topic_b"], r["mode"])
    if kind == "topic":
        return _select_field(KB[r["topic"]], r["mode"], r["qtype"])
    return _fallback_with_suggestions(r["text"])


@functools.lru_cache(maxsize=4096)
def _answer_cached(query: str, mode: str | None = None) -> str:
    """Cached wrapper around _core_answer — repeated identical questions
    (common with many students asking the same FAQ) skip re-matching."""
    return _core_answer(query, mode)


def answer(query, mode=None):
    """Public entry point. Always returns a plain string, never raises."""
    query = str(query or "").strip()
    if not query:
        return "Please enter a Social Science question."
    if len(query) > 600:
        query = query[:600]
    if mode is not None and mode not in MODES:
        mode = _MODE_ALIASES.get(str(mode).lower().strip(), None)
    try:
        return _answer_cached(query, mode)
    except Exception:  # never let a bad input crash the server
        return FALLBACK_MESSAGE


# ---------------------------------------------------------------------------
# 12. THE 1-LAKH QUESTION BANK  (every way of asking, generated + tested)
# ---------------------------------------------------------------------------
# HOW THE "1 LAKH" IS MADE — AND WHAT IT IS (AND ISN'T):
#   The bank is generated from  (topic names/aliases)  x  (question styles)
#   x  (polite/casual wrappers). Every question is a DIFFERENT WAY OF ASKING
#   about the ~35 textbook topics in KB — "what is", "define", "explain in
#   detail", "short note", "why important", "causes", "effects", "examples",
#   "how does it work", "who/when/where", "for 3 marks", Hinglish, typos...
#   It is NOT 100,000 different facts: inventing facts would break the
#   accuracy rule of this project. Every answer still comes from the
#   hand-checked NCERT notes in KB. Use self_test() to measure how many of
#   these questions the engine resolves to the right topic.

_T = {}  # style name -> list of templates with {t}

_T["definition"] = [
    "what is {t}", "what are {t}", "define {t}", "definition of {t}",
    "meaning of {t}", "what do you mean by {t}", "what does {t} mean",
    "explain the term {t}", "explain the concept of {t}",
    "tell me what {t} is", "can you define {t}", "please define {t}",
    "give the definition of {t}", "what is meant by {t}", "{t} meaning",
    "{t} definition", "{t} kya hai", "{t} kya hota hai",
    "{t} ka matlab kya hai", "{t} ka arth batao", "whats {t}", "wat is {t}",
    "i want to know what {t} is", "do you know what {t} is",
    "define the term {t}", "state the meaning of {t}",
    "what is the meaning of {t}", "briefly define {t}",
    "one line definition of {t}", "what exactly is {t}",
    "can you tell me what {t} is", "could you explain what {t} means",
    "give me the meaning of {t}", "{t} ka meaning batao",
]
_T["explain"] = [
    "explain {t}", "explain {t} in detail", "explain {t} in short",
    "explain {t} briefly", "explain {t} in simple words",
    "explain {t} in easy language", "explain {t} to me",
    "can you explain {t}", "could you please explain {t}",
    "please explain {t}", "describe {t}", "describe {t} in detail",
    "discuss {t}", "discuss {t} in detail", "elaborate {t}",
    "elaborate on {t}", "tell me about {t}", "tell me something about {t}",
    "tell me everything about {t}", "i want to learn about {t}",
    "teach me {t}", "help me understand {t}", "i did not understand {t}",
    "what do you know about {t}", "give me information on {t}",
    "give an overview of {t}", "overview of {t}", "introduction to {t}",
    "write about {t}", "write a paragraph on {t}", "write an essay on {t}",
    "write a detailed answer on {t}", "answer in detail: {t}", "{t} explain",
    "{t} explanation", "{t} in detail", "{t} in brief", "{t} samjhao",
    "{t} ke bare mein batao", "{t} ke baare mein bataiye",
    "mujhe {t} samjhao", "{t} ko explain karo", "i need to understand {t}",
    "give me a full explanation of {t}", "make me understand {t}",
    "explain {t} step by step", "explain {t} like i am 5",
    "explain {t} for beginners", "what should i know about {t}",
    "{t}", "{t} class 9",
]
_T["short_note"] = [
    "short note on {t}", "write a short note on {t}",
    "write short notes on {t}", "notes on {t}", "make notes on {t}",
    "give me notes on {t}", "{t} short note", "{t} notes",
    "{t} short notes for exam", "quick revision of {t}", "revise {t}",
    "revision notes on {t}", "summary of {t}", "summarise {t}",
    "summarize {t}", "key points of {t}", "important points of {t}",
    "important points on {t}", "{t} in points", "{t} in bullet points",
    "explain {t} in points", "cheat sheet for {t}", "bullet points on {t}",
    "pointwise {t}", "{t} ke notes", "{t} short note likho",
    "{t} ke important points", "main points of {t}", "make a summary of {t}",
    "short: {t}", "short note: {t}",
]
_T["short"] = [
    "{t} in one line", "explain {t} in one line",
    "explain {t} in one sentence", "{t} in 2 lines", "in short {t}",
    "briefly explain {t}", "in brief what is {t}", "short answer: {t}",
    "quick answer {t}", "one line answer for {t}",
    "give a short answer on {t}", "{t} in a nutshell",
    "{t} in simple words", "what is {t} in simple words",
    "what is {t} in easy words", "what is {t} briefly",
    "{t} ko short mein batao", "{t} in 1 line", "very short answer: {t}",
    "quickly tell me about {t}", "short: what is {t}", "brief: {t}",
]
_T["importance"] = [
    "why is {t} important", "importance of {t}", "significance of {t}",
    "what is the importance of {t}", "what is the significance of {t}",
    "what is the role of {t}", "role of {t}", "why should we study {t}",
    "why is {t} needed", "need of {t}", "what is the purpose of {t}",
    "purpose of {t}", "benefits of {t}", "uses of {t}",
    "why {t} is important for us", "explain the importance of {t}",
    "write the importance of {t}", "state the significance of {t}",
    "{t} ka mahatva", "{t} kyu zaroori hai", "{t} kyu important hai",
    "how is {t} useful", "how does {t} help us", "what is the value of {t}",
    "why do we need {t}", "{t} importance", "{t} significance",
    "why do {t} matter", "what is the relevance of {t}",
]
_T["features"] = [
    "features of {t}", "main features of {t}", "what are the features of {t}",
    "characteristics of {t}", "salient features of {t}",
    "key features of {t}", "principles of {t}", "list the features of {t}",
    "name the features of {t}", "enumerate the features of {t}",
    "state the features of {t}", "mention the features of {t}",
    "what are the main points of {t}", "elements of {t}",
    "components of {t}", "{t} features", "{t} characteristics",
    "{t} ki visheshta", "{t} ki visheshtayein batao",
    "explain the features of {t}", "list points about {t}",
    "give the main features of {t}", "write any three features of {t}",
    "write any five points on {t}", "what are the key parts of {t}",
    "what are the different parts of {t}", "classification of {t}",
    "what are the characteristics of {t}", "basic features of {t}",
]
_T["causes"] = [
    "causes of {t}", "what are the causes of {t}", "what causes {t}",
    "reasons for {t}", "reasons behind {t}", "why does {t} happen",
    "why did {t} happen", "why {t} happens", "why does {t} occur",
    "how does {t} occur", "what led to {t}", "factors responsible for {t}",
    "factors affecting {t}", "origin of {t}", "how did {t} start",
    "how did {t} begin", "explain the causes of {t}",
    "state the causes of {t}", "list the causes of {t}",
    "write the reasons for {t}", "{t} causes", "{t} ke karan",
    "{t} kyu hota hai", "{t} kaise hota hai", "what are the reasons for {t}",
    "what is the reason behind {t}", "how is {t} caused",
    "what are the reasons behind {t}",
]
_T["effects"] = [
    "effects of {t}", "what are the effects of {t}", "impact of {t}",
    "what is the impact of {t}", "consequences of {t}",
    "what are the consequences of {t}", "results of {t}", "outcome of {t}",
    "what happens because of {t}", "what happened after {t}",
    "how does {t} affect us", "how does {t} affect people",
    "how does {t} affect life", "influence of {t}",
    "explain the effects of {t}", "state the effects of {t}",
    "list the effects of {t}", "write the impact of {t}", "{t} effects",
    "{t} impact", "{t} ka prabhav", "{t} ke parinam",
    "what are the results of {t}", "what changes does {t} bring",
    "what is the effect of {t}", "how does {t} influence society",
]
_T["examples"] = [
    "examples of {t}", "give examples of {t}", "give an example of {t}",
    "example of {t}", "real life examples of {t}",
    "real life example of {t}", "examples related to {t}",
    "illustrate {t} with examples", "explain {t} with examples",
    "explain {t} with an example", "{t} examples", "{t} ka udaharan",
    "{t} ke udaharan batao", "case study on {t}", "case study of {t}",
    "give a case study on {t}", "give examples to explain {t}",
]
_T["process"] = [
    "how does {t} work", "how is {t} formed", "how {t} works",
    "how to understand {t}", "process of {t}", "working of {t}",
    "mechanism of {t}", "steps in {t}", "explain how {t} works",
    "describe the process of {t}", "how {t} happens", "how is {t} done",
    "how {t} is done", "how did {t} develop", "how does {t} operate",
]
_T["fact"] = [
    "who is associated with {t}", "when did {t} happen", "where is {t}",
    "which is {t}", "name the {t}", "state {t}", "mention {t}",
    "when was {t}", "where did {t}", "who gave {t}", "who proposed {t}",
    "how many {t} are there", "how much {t}", "which {t}", "name {t}",
    "give one fact about {t}", "give some facts about {t}",
    "facts about {t}", "tell me a fact about {t}", "fun fact about {t}",
    "who discovered {t}", "which year {t}",
]
_T["exam"] = [
    "{t} 1 mark question", "{t} 2 marks answer", "{t} for 3 marks",
    "{t} for 5 marks", "answer for 2 marks: {t}", "answer for 3 marks: {t}",
    "answer for 5 marks: {t}", "write in 3 marks: {t}",
    "important question: {t}", "very important question on {t}",
    "exam question on {t}", "board exam answer on {t}",
    "ncert answer for {t}", "ncert question: {t}", "class 9 {t}",
    "class 9 sst {t}", "class 9 {t} answer", "sst {t}", "{t} class 9 ncert",
    "q. explain {t}", "q. write a short note on {t}", "ques: what is {t}",
    "answer the following question: what is {t}",
    "long answer question on {t}", "short answer question on {t}",
    "very short answer question on {t}", "hots question on {t}",
    "higher order thinking question on {t}",
    "application based question on {t}", "situation based question on {t}",
    "case based question on {t}", "mcq on {t}", "true or false {t}",
    "fill in the blanks {t}", "assertion reason {t}",
    "1 mark: {t}", "2 marks: {t}", "3 marks: {t}", "5 marks: {t}",
    "exam tomorrow, explain {t}", "revise {t} before exam",
]

# how a student might wrap ANY of the above
_PREFIXES = [
    "", "please ", "pls ", "sir ", "mam ", "hey ", "hi ", "hello ",
    "hi sst ai, ", "sst ai ", "can you tell me ", "could you tell me ",
    "i want to know ", "i need to know ", "tell me ", "bhai ", "kindly ",
    "excuse me, ", "quick question: ", "doubt: ", "my doubt is ",
    "hello sir ", "good morning ", "ok so ", "one more question ",
]
_SUFFIXES = [
    "", "?", " please", " pls", " sir", " for exam", " for class 9",
    " ncert", " answer", " thanks", " urgent", " fast", " today",
]

_QUESTION_WORD_START = {
    "what", "why", "how", "who", "when", "where", "which", "does", "do",
    "is", "are", "define", "difference", "list", "explain", "compare",
}


def _generation_subjects() -> list[tuple[str, str]]:
    """(subject phrase, topic key) pairs safe to drop into a template:
    real topic names / aliases that are noun phrases, not questions."""
    subjects, seen = [], set()
    for key, e in KB.items():
        for cand in [key.replace("_", " ")] + list(e.get("aliases", [])):
            n = _normalise(cand)
            w = n.split()
            if not n or n in seen or len(w) > 5:
                continue
            if w[0] in _QUESTION_WORD_START or "vs" in w or "difference" in w:
                continue
            seen.add(n)
            subjects.append((n, key))
    return subjects


def _standalone_questions() -> list[tuple[str, str, str]]:
    """Aliases that are already complete questions ('what causes
    earthquakes', 'why are elections important', ...)."""
    out, seen = [], set()
    for key, e in KB.items():
        for cand in e.get("aliases", []):
            n = _normalise(cand)
            w = n.split()
            if n and w and (w[0] in _QUESTION_WORD_START or "difference" in w) and n not in seen:
                seen.add(n)
                out.append((n, key, "standalone"))
    return out


def iter_supported_questions(limit: int | None = None):
    """Yield (question, topic_key, style) — every distinct way of asking
    that the engine is tested against. Order is style-major/topic-inner so
    that any prefix of the stream is spread evenly over all topics."""
    subjects = _generation_subjects()
    seen: set[str] = set()
    count = 0

    def emit(q, key, style):
        nonlocal count
        norm = _normalise(q)
        if not norm or norm in seen:
            return None
        seen.add(norm)
        count += 1
        return (q.strip(), key, style)

    for q, key, style in _standalone_questions():
        item = emit(q, key, style)
        if item:
            yield item
            if limit and count >= limit:
                return

    w = 0  # running counter for rotating wrappers
    for style, templates in _T.items():
        for tpl in templates:
            for subj, key in subjects:
                base = tpl.format(t=subj)
                item = emit(base, key, style)
                if item:
                    yield item
                    if limit and count >= limit:
                        return
                w += 1
                wrapped = (_PREFIXES[w % len(_PREFIXES)] + base +
                           _SUFFIXES[(w // len(_PREFIXES)) % len(_SUFFIXES)])
                item = emit(wrapped, key, style)
                if item:
                    yield item
                    if limit and count >= limit:
                        return


QUESTION_BANK_TARGET = 100_000   # "1 lakh"


def count_supported_questions() -> int:
    """How many distinct question phrasings the generator produces."""
    return sum(1 for _ in iter_supported_questions())


def export_question_bank(path: str, limit: int = QUESTION_BANK_TARGET) -> int:
    """Write the question bank to a CSV (id, question, topic, chapter,
    subject, style). Returns the number of rows written. Rows are spread
    evenly across topics and styles."""
    import csv
    items = list(iter_supported_questions())
    if limit and len(items) > limit:
        items = [items[int(i * len(items) / limit)] for i in range(limit)]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow(["id", "question", "topic", "chapter", "subject", "style"])
        for i, (q, key, style) in enumerate(items, 1):
            wr.writerow([i, q, key, KB[key].get("chapter", ""),
                         topic_subject(key), style])
    return len(items)


def self_test(limit: int | None = None, show_failures: int = 15) -> dict:
    """Run the generated question bank through the real resolver and
    report how many land on the intended topic. This is the honest
    measure of how well the engine understands all these ways of asking."""
    total = ok = 0
    by_style: dict[str, list[int]] = {}
    failures = []
    for q, key, style in iter_supported_questions(limit):
        r = resolve(q)
        got = r.get("topic")
        good = (got == key)
        total += 1
        ok += good
        s = by_style.setdefault(style, [0, 0])
        s[0] += 1
        s[1] += good
        if not good and len(failures) < show_failures:
            failures.append((q, key, got, r["kind"]))
    return {
        "total": total, "correct": ok,
        "accuracy": round(100 * ok / total, 2) if total else 0.0,
        "by_style": {k: (v[0], round(100 * v[1] / v[0], 1)) for k, v in by_style.items()},
        "sample_failures": failures,
    }


# ---------------------------------------------------------------------------
# 13. COMMAND LINE  (python knowledge.py --ask "what is democracy")
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    if args[:1] == ["--ask"] and len(args) > 1:
        print(answer(" ".join(args[1:])))
    elif args[:1] == ["--stats"]:
        print("Topics:", len(KB))
        print("Distinct question phrasings:", count_supported_questions())
    elif args[:1] == ["--test"]:
        n = int(args[1]) if len(args) > 1 else None
        print(self_test(n))
    elif args[:1] == ["--export"]:
        p = args[1] if len(args) > 1 else "question_bank.csv"
        print("Rows written:", export_question_bank(p))
    else:
        print("Usage: python knowledge.py --ask \"question\" | --stats | "
              "--test [N] | --export [file.csv]")
