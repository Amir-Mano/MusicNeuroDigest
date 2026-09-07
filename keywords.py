"""Weighted keyword list used to rank articles by relevance to Amir's PhD research
(Neuroplasticity in Music Learning: A Multimodal MRI Approach to Musical Features and
Instrument-Specific Characteristics, Sagol School of Neuroscience, TAU, supervised by
Prof. Yaniv Assaf).

Edit this file directly to tune the digest as the research focus evolves -- no other
code needs to change. relevance.py imports KEYWORDS and does the scoring; this file is
just data.

Format: (keyword, weight) tuples. Weight is roughly:
  5 = central to the current project (instrument-specific work, core methods)
  3-4 = strongly relevant (related methods, populations, regions)
  2 = generally relevant (broader music-neuroplasticity literature)
  1 = general neuroimaging catch-all, keeps recall wide

Matching is case-insensitive substring matching (see relevance.py); title matches count
2x, abstract matches count 1x.
"""

KEYWORDS = [
    # --- Population / study design: musicians vs. non-musicians, longitudinal learning ---
    ("musician", 2), ("musicians", 2), ("non-musician", 2), ("non-musicians", 2),
    ("instrumentalist", 3), ("instrumentalists", 3),
    ("music training", 3), ("musical training", 3), ("music learning", 3), ("musical learning", 3),
    ("skill learning", 2), ("skill acquisition", 2), ("procedural learning", 2), ("expertise", 2),
    ("cross-sectional", 1), ("longitudinal", 2), ("predisposition", 2), ("nature vs nurture", 2),

    # --- Instruments: instrument-specific differences are a central hypothesis of the PhD ---
    ("trumpet", 5), ("trombone", 5), ("brass", 3), ("embouchure", 4),
    ("wind instrument", 3), ("wind instruments", 3),
    ("guitarist", 2), ("guitarists", 2), ("pianist", 2), ("pianists", 2), ("keyboardist", 2),
    ("string instrument", 2), ("string instruments", 2), ("percussionist", 2),

    # --- Neuroplasticity (core concept) ---
    ("neuroplasticity", 3), ("neural plasticity", 3), ("plasticity", 2),
    ("cortical reorganization", 3), ("structural plasticity", 3),

    # --- Multimodal MRI methods used in the project ---
    ("multimodal mri", 3), ("diffusion mri", 3), ("diffusion tensor imaging", 2),
    ("dti", 2), ("dwi", 2), ("mean diffusivity", 3), ("fractional anisotropy", 2),
    ("tractography", 3), ("gray matter volume", 3), ("grey matter volume", 3),
    ("gray matter", 2), ("grey matter", 2), ("white matter", 2), ("cortical thickness", 2),

    # --- Functional / connectome methods ---
    ("resting-state fmri", 3), ("resting state fmri", 3), ("functional connectivity", 3),
    ("structural connectome", 3), ("functional connectome", 3), ("connectome", 3),
    ("connectomics", 2), ("graph theory", 2), ("network analysis", 2),
    ("node degree", 2), ("betweenness centrality", 2),

    # --- Naturalistic fMRI / intersubject correlation: newer, distinctive part of the project ---
    ("naturalistic fmri", 4), ("intersubject correlation", 4), ("inter-subject correlation", 4),
    ("isc", 1), ("naturalistic stimuli", 3), ("naturalistic viewing", 3),

    # --- Auditory-motor integration / sensorimotor (theoretical core) ---
    ("auditory-motor", 4), ("audiomotor", 4), ("sensorimotor integration", 3), ("sensorimotor", 2),
    ("motor learning", 3),

    # --- Brain regions that recur in his own findings ---
    ("cerebellum", 3), ("motor cortex", 2), ("premotor cortex", 3), ("primary motor cortex", 2),
    ("auditory cortex", 2), ("broca", 2), ("wernicke", 2), ("fusiform gyrus", 2),

    # --- General neuroimaging catch-all (keeps recall wide) ---
    ("neuroimaging", 1), ("fmri", 1), ("mri", 1), ("eeg", 1), ("meg", 1),
]
