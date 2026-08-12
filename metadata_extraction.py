"""Skill: extract lightweight structured metadata from an article -- study
type, method/metrics, and reported sample size -- from PubMed's own
publication-type tags plus local keyword/regex heuristics on the abstract.

Purely local, no network calls. Best-effort by nature: abstracts don't
always state sample sizes or design cleanly in free text, so results here
are a reading aid, not a substitute for reading the actual paper.
"""

import re

# PubMed's own MeSH publication-type tags worth surfacing; anything outside
# this set (e.g. generic "Journal Article", "English Abstract") is dropped
# so it doesn't crowd out the more informative text-based fallback below.
_INFORMATIVE_PUBLICATION_TYPES = {
    "Review", "Systematic Review", "Meta-Analysis", "Randomized Controlled Trial",
    "Clinical Trial", "Comparative Study", "Case Reports", "Multicenter Study",
    "Observational Study", "Validation Study", "Twin Study",
}

# Fallback: study-design language authors commonly use in abstracts, checked
# only when PubMed's own tags didn't yield anything informative.
_DESIGN_PATTERNS = [
    (r"\blongitudinal\b", "Longitudinal study"),
    (r"\bcross[- ]sectional\b", "Cross-sectional study"),
    (r"\bcase[- ]control\b", "Case-control study"),
    (r"\bcohort study\b", "Cohort study"),
    (r"\bpilot study\b", "Pilot study"),
    (r"\btraining study\b", "Training/intervention study"),
    (r"\bintervention\b", "Intervention study"),
    (r"\bprospective\b", "Prospective study"),
    (r"\bretrospective\b", "Retrospective study"),
]


def classify_study_type(article: dict) -> str:
    pub_types = [
        t for t in article.get("publication_types", [])
        if t in _INFORMATIVE_PUBLICATION_TYPES
    ]
    if pub_types:
        return " / ".join(pub_types)

    text = f"{article.get('title', '')} {article.get('abstract', '')}".lower()
    for pattern, label in _DESIGN_PATTERNS:
        if re.search(pattern, text):
            return label

    return "Original research (design not specified in abstract)"


# Broad modality first, then modality-specific metrics/analyses. Short
# acronyms (FA, MD, ERP...) are only checked once their parent modality is
# confirmed present, to avoid false positives on bare 2-3 letter matches.
_MODALITY_PATTERNS = [
    (r"\bfunctional mri\b|\bfmri\b", "fMRI"),
    (
        r"\bdiffusion tensor imaging\b|\bdti\b|\bdiffusion mri\b|\bdiffusion-weighted\b",
        "diffusion MRI",
    ),
    (
        r"\bvoxel-based morphometry\b|\bvbm\b|\bstructural mri\b"
        r"|\bgray matter volume\b|\bgrey matter volume\b|\bcortical thickness\b",
        "structural MRI",
    ),
    (r"\belectroencephalograph\w*\b|\beeg\b", "EEG"),
    (r"\bmagnetoencephalograph\w*\b|\bmeg\b", "MEG"),
    (r"\bpositron emission tomography\b|\bpet imaging\b|\bpet scan\w*\b", "PET"),
    (
        r"\bfunctional near-infrared spectroscopy\b|\bfnirs\b|\bnear-infrared spectroscopy\b",
        "fNIRS",
    ),
    (r"\btranscranial magnetic stimulation\b|\btms\b", "TMS"),
    (r"\bmagnetic resonance spectroscopy\b|\bmrs\b", "MRS"),
    (r"\bbehaviou?ral\b|\bpsychophysic\w*\b", "behavioral/psychophysical"),
]

_FMRI_METRIC_PATTERNS = [
    (r"\bresting[- ]state\b", "resting-state"),
    (r"\btask-based\b|\btask-related\b", "task-based"),
    (r"\bgraph theor\w*\b", "graph theory"),
    (r"\beffective connectivity\b", "effective connectivity"),
    (r"\bfunctional connectivity\b", "functional connectivity"),
    (r"\bindependent component analys\w*\b|\bica\b", "ICA"),
    (r"\bseed-based\b", "seed-based connectivity"),
    (r"\binter-subject correlation\b|\bisc\b", "ISC"),
    (r"\bmulti-?voxel pattern analys\w*\b|\bmvpa\b", "MVPA"),
    (r"\bmachine learning\b|\bclassif\w*\b|\bdecoding\b", "machine learning/decoding"),
    (r"\bamplitude of low[- ]frequency fluctuation\w*\b|\balff\b", "ALFF"),
    (r"\bregional homogeneity\b|\breho\b", "ReHo"),
]

_DIFFUSION_METRIC_PATTERNS = [
    (r"\bfractional anisotropy\b", "FA"),
    (r"\bmean diffusivity\b", "MD"),
    (r"\bradial diffusivity\b", "RD"),
    (r"\baxial diffusivity\b", "AD"),
    (r"\btractograph\w*\b", "tractography"),
    (r"\bgraph theor\w*\b", "graph theory"),
]

_EEG_METRIC_PATTERNS = [
    (r"\bevent-related potential\w*\b|\berp\b", "ERP"),
    (r"\boscillation\w*\b", "oscillations"),
    (r"\bpower spectr\w*\b", "power spectral analysis"),
    (r"\bcoherence\b", "coherence"),
    (r"\bsource localization\b|\bsource localisation\b", "source localization"),
    (r"\bconnectivity\b", "connectivity"),
]

_METRIC_PATTERNS_BY_MODALITY = {
    "fMRI": _FMRI_METRIC_PATTERNS,
    "diffusion MRI": _DIFFUSION_METRIC_PATTERNS,
    "EEG": _EEG_METRIC_PATTERNS,
    "MEG": _EEG_METRIC_PATTERNS,
}


def _find_all(text: str, patterns: list) -> list:
    found = []
    for pattern, label in patterns:
        if re.search(pattern, text) and label not in found:
            found.append(label)
    return found


def extract_methods(article: dict) -> str:
    text = f"{article.get('title', '')} {article.get('abstract', '')}".lower()

    modalities = _find_all(text, _MODALITY_PATTERNS)
    if not modalities:
        return "Not specified in abstract"

    parts = []
    for modality in modalities:
        metric_patterns = _METRIC_PATTERNS_BY_MODALITY.get(modality)
        metrics = _find_all(text, metric_patterns) if metric_patterns else []
        parts.append(f"{modality} ({', '.join(metrics)})" if metrics else modality)
    return "; ".join(parts)


# "32 musicians and 28 controls" style mentions -- checked first since they
# carry a group label. Falls back to bare "N = 32" / "n=45" style notation.
_GROUP_COUNT_PATTERN = re.compile(
    r"\b(\d{1,4})\s+(musicians?|non-musicians?|controls?|healthy controls?|patients?|"
    r"participants?|subjects?|children|adults?|volunteers?|listeners?|"
    r"trombonists?|instrumentalists?)\b",
    re.IGNORECASE,
)
_N_EQUALS_PATTERN = re.compile(r"\bn\s*=\s*(\d{1,4})\b", re.IGNORECASE)


def extract_sample_size(article: dict) -> str:
    abstract = article.get("abstract", "")

    group_matches = _GROUP_COUNT_PATTERN.findall(abstract)
    if group_matches:
        seen = []
        for count, label in group_matches:
            entry = f"{count} {label.lower()}"
            if entry not in seen:
                seen.append(entry)
        return ", ".join(seen)

    n_matches = _N_EQUALS_PATTERN.findall(abstract)
    if n_matches:
        unique_ns = sorted({int(n) for n in n_matches})
        return ", ".join(f"N = {n}" for n in unique_ns)

    return "Not clearly stated in abstract"
