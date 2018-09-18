#!/usr/bin/env python
# cardinal_pythonlib/psychiatry/drugs.py

"""
===============================================================================

    Original code copyright (C) 2009-2018 Rudolf Cardinal (rudolf@pobox.com).

    This file is part of cardinal_pythonlib.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

===============================================================================

**Drug information, with an emphasis on psychotropic drugs, including 
translating specific to generic names.**

**Examples**

Test within Python:

.. code-block:: python

    from cardinal_pythonlib.drugnames import drug_name_to_generic

    drug_name_to_generic("UNKNOWN")
    drug_name_to_generic("UNKNOWN", unknown_to_default=True)
    drug_names_to_generic([
        "citalopram", "Citalopram", "Cipramil", "Celexa",
        "olanzepine",  # typo
        "dextroamphetamine",
        "amitryptyline",
    ])

**Antidepressants**

As of 2018-07-01, this is a functional superset of the SLAM
antidepressant-finding SQL (see ``dep_med_v1``), though mainly a superset in
non-antidepressant respects; the only antidepressants it adds are:

- buproprion, maprotiline

The SLAM antidepressant finder finds:

- tricyclic (category)
- amitriptyline, clomipramine, dosulepin, doxepin, imipramine, lofepramine,
  nortriptyline, trimipramine
- mianserin, trazodone, phenelzine, isocarboxazid, tranylcypromine, moclobemide
- citalopram, escitalopram, fluoxetine, fluvoxamine, paroxetine, sertraline
- mirtazapine, reboxetine, venlafaxine, agomelatine, duloxetine
- flupentixol, tryptophan

Sorted, that is:

.. code-block:: none

    agomelatine
    amitriptyline
    citalopram
    clomipramine
    dosulepin
    doxepin
    duloxetine
    escitalopram
    fluoxetine
    flupentixol
    fluvoxamine
    imipramine
    isocarboxazid
    lofepramine
    mianserin
    mirtazapine
    moclobemide
    nortriptyline
    paroxetine
    phenelzine
    reboxetine
    sertraline
    tranylcypromine
    trazodone
    tricyclic
    trimipramine
    tryptophan
    venlafaxine

Compare that against the output of:

.. code-block:: python

    [x.generic_name for x in all_drugs_where(slam_antidepressant_finder=True,
                                             include_categories=True)]

**Using this code from R via reticulate**

Test within R:

.. code-block:: r

    # -------------------------------------------------------------------------
    # Load libraries
    # -------------------------------------------------------------------------
    
    RUN_ONCE_ONLY <- '
        library(devtools)
        devtools::install_github("rstudio/reticulate")  # get latest version
    '

    library(data.table)
    library(reticulate)

    # -------------------------------------------------------------------------
    # Set up reticulate
    # -------------------------------------------------------------------------

    VENV <- "~/dev/venvs/cardinal_pythonlib"  # or your preferred virtualenv
    PYTHON_EXECUTABLE <- ifelse(
        .Platform$OS.type == "windows",
        file.path(VENV, "Scripts", "python.exe"),  # Windows
        file.path(VENV, "bin", "python")  # Linux
    )
    reticulate::use_python(PYTHON_EXECUTABLE, required=TRUE)
    # ... it is CRITICAL to use required=TRUE, or it might fail silently
    
    # Unnecessary now reticulate::use_python() works:
    # 
    # PYTHON_VERSION <- "python3.5"
    # CARDINAL_PYTHONLIB_BASEDIR <- ifelse(
    #     .Platform$OS.type == "windows",
    #     file.path(VENV, "lib", "site-packages/cardinal_pythonlib"),
    #     file.path(VENV, "lib", PYTHON_VERSION, "site-packages/cardinal_pythonlib")
    # )
    # reticulate::use_virtualenv(VENV, required=TRUE)
    #
    # cpl_fileops <- reticulate::import_from_path("fileops", CARDINAL_PYTHONLIB_BASEDIR)
    # cpl_drugs <- reticulate::import_from_path("drugs", file.path(CARDINAL_PYTHONLIB_BASEDIR, "psychiatry"))
    #
    # ... this is NOT WORKING properly; dotted imports via reticulate::import() fail; also, imports from
    # within the Python code fail even if you use reticulate::import_from_path(); this suggests the virtualenv is not set up
    # properly; use reticulate::use_python() instead.

    # -------------------------------------------------------------------------
    # Import Python modules
    # -------------------------------------------------------------------------

    cardinal_pythonlib <- reticulate::import("cardinal_pythonlib")
    cpl_fileops <- reticulate::import("cardinal_pythonlib.fileops")
    cpl_drugs <- reticulate::import("cardinal_pythonlib.psychiatry.drugs")

    # -------------------------------------------------------------------------
    # Do something useful
    # -------------------------------------------------------------------------

    testnames <- c("citalopram", "Cipramil", "Prozac", "fluoxetine")
    # Works for simple variables:
    cpl_drugs$drug_names_to_generic(testnames)

    # Also works for data table replacements:
    dt <- data.table(
        subject = c("Alice", "Bob", "Charles", "Dawn", "Egbert", "Flora"),
        drug = c("citalopram", "Cipramil", "Prozac", "fluoxetine", "Priadel", "Haldol")
    )
    dt[, drug_generic := cpl_drugs$drug_names_to_generic(drug)]
    dt[, is_antidepressant := cpl_drugs$drug_names_match_criteria(
            drug_generic, 
            names_are_generic=TRUE,
            antidepressant=TRUE)]
    dt[, is_antidepressant_not_ssri := cpl_drugs$drug_names_match_criteria(
            drug_generic, 
            names_are_generic=TRUE,
            antidepressant=TRUE,
            ssri=FALSE)]
    dt[, is_conventional_antidepressant := cpl_drugs$drug_names_match_criteria(
            drug_generic, 
            names_are_generic=TRUE,
            conventional_antidepressant=TRUE)]
    dt[, slam_antidepressant_finder := cpl_drugs$drug_names_match_criteria(
            drug_generic, 
            names_are_generic=TRUE,
            slam_antidepressant_finder=TRUE,
            include_categories=TRUE)]

"""  # noqa

import re
from typing import Dict, List, Optional, Union


# =============================================================================
# Regex constants
# =============================================================================

WILDCARD = ".*"  # if re.DOTALL is set, this also matches newlines
WB = WORD_BOUNDARY = r"\b"


# =============================================================================
# Class to capture drug information
# =============================================================================

class Drug(object):
    """
    Class to describe a specific drug, or a drug category.

    Also embodies knowledge about brand names and common misspellings.

    See the :const:`DRUGS` list for example of use.
    """
    def __init__(
            self,
            # Names
            generic: Union[str, List[str]],
            alternatives: List[str] = None,
            category_not_drug: bool = False,
            add_preceding_wildcards: bool = True,
            add_preceding_word_boundary: bool = True,
            add_following_wildcards: bool = True,
            # Psychiatry
            psychotropic: bool = None,  # special; can be used as override if False  # noqa
            antidepressant: bool = False,
            conventional_antidepressant: bool = False,
            ssri: bool = False,
            non_ssri_modern_antidepressant: bool = False,
            tricyclic_antidepressant: bool = False,
            tetracyclic_and_related_antidepressant: bool = False,
            monoamine_oxidase_inhibitor: bool = False,
            antipsychotic: bool = False,
            first_generation_antipsychotic: bool = False,
            second_generation_antipsychotic: bool = False,
            stimulant: bool = False,
            anticholinergic: bool = False,
            benzodiazepine: bool = False,
            z_drug: bool = False,
            non_benzodiazepine_anxiolytic: bool = False,
            gaba_a_functional_agonist: bool = False,
            gaba_b_functional_agonist: bool = False,
            mood_stabilizer: bool = False,
            # Endocrinology
            antidiabetic: bool = False,
            sulfonylurea: bool = False,
            biguanide: bool = False,
            glifozin: bool = False,
            glp1_agonist: bool = False,
            dpp4_inhibitor: bool = False,
            meglitinide: bool = False,
            thiazolidinedione: bool = False,
            # Cardiovascular
            cardiovascular: bool = False,
            beta_blocker: bool = False,
            ace_inhibitor: bool = False,
            statin: bool = False,
            # Respiratory
            respiratory: bool = False,
            beta_agonist: bool = False,
            # Gastrointestinal
            gastrointestinal: bool = False,
            proton_pump_inhibitor: bool = False,
            nonsteroidal_anti_inflammatory: bool = False,
            # Nutritional
            vitamin: bool = False,
            # Special flags:
            slam_antidepressant_finder: bool = False) -> None:
        # noinspection PyUnresolvedReferences
        """
        Initialize and determine/store category knowledge.

        ``alternatives`` can include regexes (as text).

        We add front/back wildcards by default; this handles all situations
        like "depot X", etc. We also add a preceding word boundary (after the
        wildcard); thus the usual transformation is ``XXX`` -> ``.*\bXXX.*``.

        Args:
            generic: generic name, or list of names
            alternatives: can include regexes (as text)

            category_not_drug: is this a drug category, not a specific drug?

            add_preceding_wildcards: when making a regex (etc.), add a wildcard
                to the start of all possibilities (generic + alternative names)
                that don't already have one?
            add_preceding_word_boundary: when making a regex (etc.), add word
                boundaries to the start of all possibilities (generic +
                alternative names) that don't already have one?
            add_following_wildcards: when making a regex (etc.), add a wildcard
                to the end of all possibilities (generic + alternative names)
                that don't already have one?

            psychotropic: a psychotropic drug?

            antidepressant: an antidepressant?
            conventional_antidepressant: a traditional antidepressant?
            ssri: a selective serotonin reuptake inhibitor (SSRI)?
            non_ssri_modern_antidepressant: a non-SSRI "modern" antidepressant?
            tricyclic_antidepressant: a tricyclic?
            tetracyclic_and_related_antidepressant: a tetracyclic or related?
            monoamine_oxidase_inhibitor: a MAO-I?

            antipsychotic: an antipsychotic?
            first_generation_antipsychotic: an FGA?
            second_generation_antipsychotic: an SGA?

            stimulant: a psychostimulant?

            anticholinergic: an anticholinergic?

            benzodiazepine: a benzodiazepine?
            z_drug: a "Z" drug (e.g. zopiclone, zolpidem, ...)
            non_benzodiazepine_anxiolytic: a non-BZ anxiolytic?
            gaba_a_functional_agonist: a GABA-A functional agonist?
            gaba_b_functional_agonist: a GABA-B functional agonist?

            mood_stabilizer: a "mood stabilizer"?

            antidiabetic: treats diabetes?
            sulfonylurea: a sulfonylurea (sulphonylurea), for diabetes?
            biguanide: a biguanide, for diabetes?
            glifozin: a glifozin, for diabetes?
            glp1_agonist: a GLP-1 agonist, for diabetes?
            dpp4_inhibitor: a DPP4 inhibitor, for diabetes?
            meglitinide: a meglitinide, for diabetes?
            thiazolidinedione: a thiazolidinedione, for diabetes?

            cardiovascular: a cardiovascular drug?
            beta_blocker: a beta adrenoceptor antagonist?
            ace_inhibitor: an ACE inhibitor?
            statin: a statin?

            respiratory: a respiratory drug?
            beta_agonist: a beta adrenoceptor agonist?

            gastrointestinal: a gastrointestinal drug?
            proton_pump_inhibitor: a PPI?
            nonsteroidal_anti_inflammatory: an NSAID?

            vitamin: a vitamin?

            slam_antidepressant_finder: a drug found by the SLAM
                antidepressant-finding code? (A bit specialized, this one!)

        Attributes:

            mixture (bool): is this a mixture of more than one drug?
                Will be set if more than one generic name is given.
            all_generics (List[str]): list of all generic names in lower case
            generic_name: generic name (or combination name like ``a_with_b``
                for mixtures of ``a`` and ``b``)
            regex: compiled case-insensitive regular expression to match
                possible names
        """
        # ---------------------------------------------------------------------
        # Name handling
        # ---------------------------------------------------------------------

        if isinstance(generic, list):
            self.mixture = True
            self.all_generics = [x.lower().strip() for x in generic]
            self.generic_name = "_with_".join(self.all_generics)
        elif isinstance(generic, str):
            self.mixture = False
            self.generic_name = generic.lower().strip()
            self.all_generics = [self.generic_name]
        else:
            raise ValueError("Bad generic_name: {!r}".format(generic))
        self.alternatives = alternatives or []  # type: List[str]
        possibilities = []  # type: List[str]
        for p in list(set(self.all_generics + self.alternatives)):
            if add_preceding_word_boundary and not p.startswith(WB):
                p = WB + p
            if add_preceding_wildcards and not p.startswith(WILDCARD):
                p = WILDCARD + p
            if add_following_wildcards and not p.endswith(WILDCARD):
                p = p + WILDCARD
            possibilities.append(p)
        regex_text = "|".join("(?:" + x + ")" for x in possibilities)
        self.regex = re.compile(regex_text, re.IGNORECASE | re.DOTALL)

        # ---------------------------------------------------------------------
        # Things we know about psychotropics
        # ---------------------------------------------------------------------

        if (ssri or non_ssri_modern_antidepressant or
                tricyclic_antidepressant or
                tetracyclic_and_related_antidepressant or
                monoamine_oxidase_inhibitor):
            conventional_antidepressant = True

        if conventional_antidepressant:
            antidepressant = True

        if first_generation_antipsychotic or second_generation_antipsychotic:
            antipsychotic = True

        if benzodiazepine or z_drug:
            gaba_a_functional_agonist = True

        if ((antidepressant or antipsychotic or stimulant or anticholinergic or
                gaba_a_functional_agonist or gaba_b_functional_agonist or
                mood_stabilizer) and
                (psychotropic is not False)):
            psychotropic = True
        if psychotropic is None:
            psychotropic = False

        # ---------------------------------------------------------------------
        # Things we know about other drugs
        # ---------------------------------------------------------------------

        if (sulfonylurea or biguanide or glifozin or glp1_agonist or
                dpp4_inhibitor or meglitinide or thiazolidinedione):
            antidiabetic = True

        if beta_blocker or ace_inhibitor:
            cardiovascular = True

        # ---------------------------------------------------------------------
        # Store category knowledge
        # ---------------------------------------------------------------------

        self.category_not_drug = category_not_drug

        self.psychotropic = psychotropic
        self.antidepressant = antidepressant
        self.conventional_antidepressant = conventional_antidepressant
        self.ssri = ssri
        self.non_ssri_modern_antidepressant = non_ssri_modern_antidepressant
        self.tricyclic = tricyclic_antidepressant
        self.tetracyclic_and_related_antidepressant = tetracyclic_and_related_antidepressant  # noqa
        self.monoamine_oxidase_inhibitor = monoamine_oxidase_inhibitor

        self.antipsychotic = antipsychotic
        self.first_generation_antipsychotic = first_generation_antipsychotic
        self.second_generation_antipsychotic = second_generation_antipsychotic

        self.stimulant = stimulant

        self.anticholinergic = anticholinergic

        self.benzodiazepine = benzodiazepine
        self.z_drug = z_drug
        self.gaba_a_functional_agonist = gaba_a_functional_agonist
        self.gaba_b_functional_agonist = gaba_b_functional_agonist
        self.non_benzodiazepine_anxiolytic = non_benzodiazepine_anxiolytic

        self.mood_stabilizer = mood_stabilizer

        self.antidiabetic = antidiabetic
        self.sulfonylurea = sulfonylurea
        self.biguanide = biguanide
        self.cardiovascular = cardiovascular
        self.beta_blocker = beta_blocker
        self.ace_inhibitor = ace_inhibitor
        self.statin = statin
        self.respiratory = respiratory
        self.beta_agonist = beta_agonist
        self.gastrointestinal = gastrointestinal
        self.proton_pump_inhibitor = proton_pump_inhibitor
        self.nonsteroidal_anti_inflammatory = nonsteroidal_anti_inflammatory
        self.vitamin = vitamin

        # ---------------------------------------------------------------------
        # Store other flags
        # ---------------------------------------------------------------------

        self.slam_antidepressant_finder = slam_antidepressant_finder

    def name_matches(self, name: str) -> bool:
        """
        Detects whether the name that's passed matches our knowledge of any of
        things that this drug might be called: generic name, brand name(s),
        common misspellings.

        The parameter should be pre-stripped of edge whitespace.
        """
        return bool(self.regex.match(name))


# Source data.
DRUGS = [
    # In comments below: (*) misspelling, capitalized for brand name, (~)
    # hybrid generic/brand name, (+) old name.

    # -------------------------------------------------------------------------
    # SSRIs
    # -------------------------------------------------------------------------
    Drug(
        "citalopram",
        ["Cipramil", "Celexa"],
        ssri=True,
        slam_antidepressant_finder=True
    ),
    Drug(
        "escitalopram",
        ["Cipralex", "Lexapro"],
        ssri=True,
        slam_antidepressant_finder=True
    ),
    Drug(
        "fluoxetine",
        ["Prozac", "Bellzac", "Oxactin", "Prozep", "Sarafem", "fluox.*"],
        # CPFT 2013: "fluoxetine  Dec"
        ssri=True,
        slam_antidepressant_finder=True
    ),
    Drug(
        "fluvoxamine",
        ["Luvox", "Faverin", "fluvoxamine.*"],  # e.g. "fluvoxamine maleate"
        ssri=True,
        slam_antidepressant_finder=True
    ),
    Drug(
        "paroxetine",
        ["Seroxat", "Paxil"],  # there are other brands elsewhere...
        ssri=True,
        slam_antidepressant_finder=True
    ),
    Drug(
        "sertraline",
        ["Lustral", "Zoloft", "Bellsert"],
        # NOT Seretra (cf. SLAM code, see email to self 2016-12-02); Seretra =
        # seratrodast = for asthma
        ssri=True,
        slam_antidepressant_finder=True
    ),

    # -------------------------------------------------------------------------
    # FIRST-GENERATION ANTIPSYCHOTICS
    # -------------------------------------------------------------------------
    Drug("benperidol", ["Anquil"], first_generation_antipsychotic=True),
    Drug("chlorpromazine", ["Largactil"], first_generation_antipsychotic=True),
    Drug(
        "flupentixol",
        ["Depixol", "Fluanxol", "flupent.*", "Depixol.*"],
        # e.g. flupenthixol, flupenthixol decanoate, flupentixol decanoate
        first_generation_antipsychotic=True,
        antidepressant=True,
        slam_antidepressant_finder=True
    ),
    Drug(
        "fluphenazine",
        ["Modecate", "fluphen.*", "Modecate.*"],
        first_generation_antipsychotic=True
    ),
    Drug(
        "haloperidol",
        [
            "Haldol", "Serenase",
            "hal[io]p.*", "Dozi.*", "Hald.*", "Serena.*",
            # NB Serenase, Serenace.
            #  CPFT 2013: haloperidol, haloperidol decanoate, Haldol, Haldol
            #  decanoate, Serenase.
        ],
        first_generation_antipsychotic=True
    ),
    Drug("levomepromazine", ["Nozinan"], first_generation_antipsychotic=True),
    Drug("pericyazine", first_generation_antipsychotic=True),
    Drug("perphenazine", ["Fentazin"], first_generation_antipsychotic=True),
    Drug(
        ["amitriptyline", "perphenazine"],
        ["Triptafen"],  # special
        first_generation_antipsychotic=True,
        tricyclic_antidepressant=True,
        slam_antidepressant_finder=True
    ),
    Drug("pimozide", ["Orap"], first_generation_antipsychotic=True),
    Drug(
        "pipotiazine",
        ["pipot.*", "Piport.*"],
        # ... actually (CPFT 2013): pipotiazine, Piportil
        first_generation_antipsychotic=True
    ),
    Drug(
        "prochlorperazine",
        ["Stemetil"],
        first_generation_antipsychotic=True
    ),
    Drug("promazine", first_generation_antipsychotic=True),
    Drug(
        "sulpiride",
        ["Dolmatil", "Sulpor"],
        first_generation_antipsychotic=True
    ),
    Drug(
        "trifluoperazine",
        ["Stelazine"],
        first_generation_antipsychotic=True
    ),
    Drug(
        "zuclopenthixol",
        ["zuclop.*", "Clopix.*", "Acc?uphase"],
        # ... actually (CPFT 2013): zuclopenthixol, zuclopenthixol acetate,
        # zuclopenthixol decanoate, Clopixol, Clopixol Decanoate, Acuphase
        first_generation_antipsychotic=True
    ),

    # -------------------------------------------------------------------------
    # SECOND-GENERATION ANTIPSYCHOTICS
    # -------------------------------------------------------------------------
    Drug(
        "amisulpride",
        ["amisulp.*", "Solian"],
        # ... actually (CPFT 2013): amisulpiride(*), amisulpride, Solian
        second_generation_antipsychotic=True
    ),
    Drug(
        "aripiprazole",
        ["Abilify", "ari?pr?ipr?azol.*"],
        second_generation_antipsychotic=True
    ),
    Drug(
        "asenapine",
        ["Saphris", "Sycrest"],
         second_generation_antipsychotic=True
    ),
    Drug(
        "clozapine",
        ["cloz.*", "Denz.*", "Zapon.*"],
        # ... actually (CPFT 2013): clozapine, Clozaril, clozepine(*)
        second_generation_antipsychotic=True
    ),
    Drug(
        "iloperidone",
        ["Fanapt", "Fanapta", "Zomaril"],
        second_generation_antipsychotic=True
    ),
    Drug("lurasidone", ["Latuda"], second_generation_antipsychotic=True),
    Drug(
        "olanzapine",
        ["olanz.*", "Zalast.*", "Zyprex.*", "Zypad.*"],
        # ... actually (CPFT 2013): olanzapine, olanzapine embonate,
        # olanz(*), olanzepine(*), olanzapin(*), Zyprexa
        second_generation_antipsychotic=True
    ),
    Drug(
        "paliperidone",
        ["Invega", "Xeplion"],
        second_generation_antipsychotic=True
    ),
    Drug(
        "quetiapine",
        ["quet.*", "Seroquel"],
        # ... actually (CPFT 2013): quetiapine, quetiepine(*), Seroquel
        second_generation_antipsychotic=True
    ),
    Drug(
        "risperidone",
        ["risp.*", "Consta"],
        # ... actually (CPFT 2013): risperidone, risperadone(*), Risperidone
        # Consta (~), Risperdal, Risperdal Consta
        second_generation_antipsychotic=True
    ),
    Drug(
        "sertindole",
        ["Serdolect", "Serlect"],
        second_generation_antipsychotic=True
    ),
    Drug("ziprasidone", second_generation_antipsychotic=True),
    Drug(
        "zotepine",  # not in UK
        ["Nipolept", "Losizopilon", "Lodopin", "Setous"],
        second_generation_antipsychotic=True
    ),

    # -------------------------------------------------------------------------
    # STIMULANTS
    # -------------------------------------------------------------------------
    Drug(
        "amfetamine",
        [".*am[ph|f]etamine.*", "Adderall"],
        # ... actually (CPFT 2013): dextroamphetamine(+), dexamfetamine
        stimulant=True
    ),
    Drug(
        "methylphenidate",
        ["Ritalin", "Concerta.*", "Equasym.*", "Medikinet.*"],
        # ... actually (CPFT 2013): methylphenidate, Ritalin, Concerta
        stimulant=True
    ),
    Drug("modafinil", ["Provigil"], stimulant=True),

    # -------------------------------------------------------------------------
    # ANTICHOLINERGICS
    # -------------------------------------------------------------------------
    Drug("benztropine", ["benzatropine"], anticholinergic=True),
    Drug("orphenadrine", ["Biorphen", "Disipal"], anticholinergic=True),
    Drug("procyclidine", ["Arpicolin", "Kemadrin"], anticholinergic=True),
    Drug("trihexyphenidyl", ["Broflex"], anticholinergic=True),

    # -------------------------------------------------------------------------
    # OTHER MODERN ANTIDEPRESSANTS
    # -------------------------------------------------------------------------
    Drug(
        "agomelatine",
        ["Valdoxan"],
        non_ssri_modern_antidepressant=True,
        slam_antidepressant_finder=True
    ),
    Drug(
        "bupropion",
        ["Zyban"],
        non_ssri_modern_antidepressant=True
        # antidepressant license in US, smoking cessation in UK
    ),
    Drug(
        "duloxetine",
        ["Cymbalta", "Yentreve", "duloxat.*"],
         non_ssri_modern_antidepressant=True,
        slam_antidepressant_finder=True
    ),
    Drug(
        "mirtazapine",
        ["mirtaz.*", "mirtazepine", "Zispin", "Mirza"],
        # ... actually (CPFT 2013): mirtazapine, mirtazepine(*), "mirtazapine
        # Dec" (?)
        non_ssri_modern_antidepressant=True,
        slam_antidepressant_finder=True
    ),
    Drug(
        "reboxetine",
        ["Edronax", "reboxat.*"],
        non_ssri_modern_antidepressant=True,
        slam_antidepressant_finder=True
    ),
    Drug(
        "tryptophan",
        ["Optimax"],
        non_ssri_modern_antidepressant=True,
        slam_antidepressant_finder=True
    ),
    Drug(
        "venlafaxine",
        ["venla.*", "Eff?exor.*"],
        # ... actually (CPFT 2013): venlafaxine, venlafaxine XL,
        non_ssri_modern_antidepressant=True,  # though obviously an SSRI too...
        slam_antidepressant_finder=True
    ),

    # -------------------------------------------------------------------------
    # TRICYCLIC AND RELATED ANTIDEPRESSANTS
    # -------------------------------------------------------------------------
    Drug(
        "tricyclic_antidepressant",
        ["tricyclic.*", "tca" + WB],
        tricyclic_antidepressant=True,
        slam_antidepressant_finder=True,
        category_not_drug=True,
    ),
    Drug(
        "amitriptyline",
        ["amitr[i|y]pt[i|y]l[i|y]n.*", "Vanatrip", "Elavil", "Endep"],
        # ... actually (CPFT 2013): amitriptyline, amitriptiline(*),
        # amitryptyline(*)
        # Triptafen = amitriptyline + perphenazine; see above.
        tricyclic_antidepressant=True,
        slam_antidepressant_finder=True
    ),
    Drug(
        "clomipramine",
        ["Anafranil.*"],
        tricyclic_antidepressant=True,
        slam_antidepressant_finder=True
    ),
    Drug(
        "dosulepin",
        ["dothiepin", "Prothiaden"],
        # ... actually (CPFT 2013): dosulepin, dothiepin(+)
        tricyclic_antidepressant=True,
        slam_antidepressant_finder=True
    ),
    Drug(
        "doxepin",
        ["Sinepin", "Sinequan", "Sinepin", "Xepin"],
        # Xepin is cream only
        tricyclic_antidepressant=True,
        slam_antidepressant_finder=True
    ),
    Drug(
        "imipramine",
        ["Tofranil"],
        tricyclic_antidepressant=True,
        slam_antidepressant_finder=True
    ),
    Drug(
        "lofepramine",
        ["Lomont"],
        tricyclic_antidepressant=True,
        slam_antidepressant_finder=True
    ),
    Drug(
        "nortriptyline",
        ["nortr.*", "Allegron", "Pamelor", "Aventyl"],
        # ... actually (CPFT 2013): nortriptyline, nortryptiline(*)
        tricyclic_antidepressant=True,
        slam_antidepressant_finder=True
    ),
    Drug(
        "trimipramine",
        ["Surmontil"],
        tricyclic_antidepressant=True,
        slam_antidepressant_finder=True
    ),

    # -------------------------------------------------------------------------
    # TETRACYCLIC-RELATED ANTIDEPRESSANTS
    # -------------------------------------------------------------------------
    Drug(
        "mianserin",
        tetracyclic_and_related_antidepressant=True,
        slam_antidepressant_finder=True
    ),
    Drug(
        "trazodone",
        ["Molipaxin"],
        tetracyclic_and_related_antidepressant=True,
        slam_antidepressant_finder=True
    ),
    Drug(
        "nefazodone",
        # discontinued for hepatotoxicity? But apparently still used in 2014
        # in the UK: http://www.bbc.co.uk/news/uk-25745824
        ["Dutonin", "Nefadar", "Serzone"],
        tetracyclic_and_related_antidepressant=True
        # brand names from https://en.wikipedia.org/wiki/Nefazodone
        # ... yup, still a trickle, mostly from Islington:
        # https://openprescribing.net/chemical/0403040T0/
    ),
    Drug(
        "maprotiline",
        ["Ludiomil"],
        tetracyclic_and_related_antidepressant=True
    ),

    # -------------------------------------------------------------------------
    # MAOIs
    # -------------------------------------------------------------------------
    Drug(
        "phenelzine",
        ["phenylethylhydrazine", "Alazin", "Nardil"],
        monoamine_oxidase_inhibitor=True,
        slam_antidepressant_finder=True
        # - SLAM code (see e-mail to self 2016-12-02) also has %Alazin%; not sure  # noqa
        #   that's right; see also
        #   http://www.druglib.com/activeingredient/phenelzine/
        # - oh, yes, it is right:
        #   https://www.pharmacompass.com/active-pharmaceutical-ingredients/alazin  # noqa
        # - phenylethylhydrazine is a synonym; see
        #   http://www.minclinic.ru/drugs/drugs_eng/B/Beta-phenylethylhydrazine.html  # noqa
    ),
    # not included: pheniprazine
    Drug(
        "isocarboxazid",
        monoamine_oxidase_inhibitor=True,
        slam_antidepressant_finder=True
    ),
    Drug(
        "moclobemide",
        ["Manerix"],
        monoamine_oxidase_inhibitor=True,
        slam_antidepressant_finder=True
    ),
    Drug(
        "tranylcypromine",
        ["Parnate"],
        monoamine_oxidase_inhibitor=True,
        slam_antidepressant_finder=True
    ),

    # -------------------------------------------------------------------------
    # BENZODIAZEPINES
    # -------------------------------------------------------------------------
    Drug(
        "benzodiazepine",
        ["benzodiazepine.*"],
        benzodiazepine=True,
        category_not_drug=True
    ),
    Drug("alprazolam", benzodiazepine=True),
    Drug("chlordiazepoxide", benzodiazepine=True),
    Drug("clobazam", benzodiazepine=True),
    Drug("clonazepam", ["Rivotril"], benzodiazepine=True),
    Drug(
        "diazepam",
        ["diaz.*", "Valium"],
        # ... actually (CPFT 2013): diazepam, diazapam(*), diazapem(*), Valium
        benzodiazepine=True
    ),
    Drug("flurazepam", ["Dalmane"], benzodiazepine=True),
    Drug("loprazolam", benzodiazepine=True),
    Drug("lorazepam", ["Ativan"], benzodiazepine=True),
    Drug("lormetazepam", benzodiazepine=True),
    Drug("midazolam", ["Hypnovel"], benzodiazepine=True),
    Drug("nitrazepam", benzodiazepine=True),
    Drug("oxazepam", benzodiazepine=True),
    Drug("temazepam", benzodiazepine=True),

    # -------------------------------------------------------------------------
    # Z-DRUGS
    # -------------------------------------------------------------------------
    Drug("zaleplon", ["Sonata"], z_drug=True),
    Drug(
        "zolpidem",
        ["zolpidem.*", "Stilnoct"],
        # ... actually (CPFT 2013): zolpidem, zolpidem tartrate
        z_drug=True
    ),
    Drug("zopiclone", ["Zimovane"], z_drug=True),

    # -------------------------------------------------------------------------
    # OTHER GABA MODULATORS
    # -------------------------------------------------------------------------
    Drug(
        "baclofen",
        [
            "Lioresal", "Lyflex", "Bacfen", "Baclof", "Bacmax", "Chinofen",
            "Parafon", "Riclofen", "Spinofen", "Spinospas", "Tefsole",
            "Gablofen", "Kemstro"
        ],
        gaba_b_functional_agonist=True
    ),

    # -------------------------------------------------------------------------
    # OTHER ANXIOLYTICS
    # -------------------------------------------------------------------------
    Drug("buspirone", ["Buspar"], non_benzodiazepine_anxiolytic=True),

    # -------------------------------------------------------------------------
    # OTHER ANTIMANIC
    # -------------------------------------------------------------------------
    Drug(
        "carbamazepine",
        ["Carbagen.*", "Tegretol.*"],
        # also Tegretol Prolonged Release (formerly Tegretol Retard)
        # ... actually (CPFT 2013): carbamazepine, Tegretol
        mood_stabilizer=True
    ),
    Drug(
        "valproate",
        [".*valp.*", "Epilim.*", "Episenta", "Epival", "Convulex", "Depakote"],
        # ... also semisodium valproate
        # ... actually (CPFT 2013): sodium valproate [chrono], valproic acid,
        # valproate, sodium valproate, sodium valporate(*), sodium valporate(*)
        # chrono, Depakote
        mood_stabilizer=True
    ),
    Drug(
        "lithium",
        ["lithium.*", "Camcolit", "Liskonum", "Priadel", "Li-Liquid"],
        # ... actually (CPFT 2013): lithium, lithium carbonate, lithium citrate
        # (curious: Priadel must be being changed to lithium...)
        antidepressant=True,
        mood_stabilizer=True
    ),

    # -------------------------------------------------------------------------
    # OTHER FOR BIPOLAR/UNIPOLAR DEPRESSION
    # -------------------------------------------------------------------------
    Drug(
        "lamotrigine",
        ["lamotrigine.*", "Lamictal"],
        mood_stabilizer=True,
        antidepressant=True,
    ),
    Drug(
        "triiodothyronine",
        ["tri-iodothyronine", "liothyronine", "Cytomel"],
        antidepressant=True,
    ),

    # -------------------------------------------------------------------------
    # GENERAL MEDICINE: DIABETES
    # -------------------------------------------------------------------------
    Drug("glibenclamide", sulfonylurea=True),
    Drug(
        "gliclazide",
        ["Zicron", "Diamicron.*", "Dacadis.*", "Vitile.*"],
        sulfonylurea=True
    ),
    Drug("glimepiride", ["Amaryl"], sulfonylurea=True),
    Drug("glipizide", ["Minodiab"], sulfonylurea=True),
    Drug("tolbutamide", sulfonylurea=True),
    Drug("metformin", ["metformin.*", "Glucophage.*"], biguanide=True),
    Drug("acarbose", ["Glucobay"], antidiabetic=True),
    Drug("dapagliflozin", ["Forxiga"], glifozin=True),
    Drug("exenatide", ["Byetta", "Bydureon"], glp1_agonist=True),
    Drug("linagliptin", ["Trajenta"], dpp4_inhibitor=True),
    Drug(["linagliptin", "metformin"], ["Jentadueto"],
         biguanide=True, dpp4_inhibitor=True),
    Drug("liraglutide", ["Victoza"], glp1_agonist=True),
    Drug("lixisenatide", ["Lyxumia"], glp1_agonist=True),
    Drug("nateglinide", ["Starlix"], meglitinide=True),
    Drug("pioglitazone", ["Actos"], thiazolidinedione=True),
    Drug(["pioglitazone", "metformin"], ["Competact"],
         thiazolidinedione=True, biguanide=True),
    Drug("repaglinide", ["Prandin"], meglitinide=True),
    Drug("saxagliptin", ["Onglyza"], dpp4_inhibitor=True),
    Drug(["saxagliptin", "metformin"], ["Komboglyze"],
         dpp4_inhibitor=True, biguanide=True),
    Drug("sitagliptin", ["Januvia"], dpp4_inhibitor=True),
    Drug(["sitagliptin", "metformin"], ["Janumet"],
         dpp4_inhibitor=True, biguanide=True),
    Drug("vildagliptin", ["Galvus"], dpp4_inhibitor=True),
    Drug(["vildagliptin", "metformin"], ["Eucreas"], 
         dpp4_inhibitor=True, biguanide=True),
    Drug(
        "insulin",
        # Insulin. Covering the BNF categories:
        # INSULIN
        # INSULIN ASPART
        # INSULIN GLULISINE
        # INSULIN LISPRO
        # INSULIN DEGLUDEC
        # INSULIN DETEMIR
        # INSULIN GLARGINE
        # INSULIN ZINC SUSPENSION
        # ISOPHANE INSULIN
        # PROTAMINE ZINC INSULIN
        # BIPHASIC INSULIN ASPART
        # BIPHASIC INSULIN LISPRO
        # BIPHASIC ISOPHANE INSULIN
        [
            ".*insulin.*", ".*aspart.*", ".*glulisine.*", ".*lispro.*",
            ".*degludec.*", ".*detemir.*", ".*glargine.*", ".*Hypurin.*",
            ".*Actrapid.*", ".*Humulin.*", ".*Insuman.*", ".*Novorapid.*",
            ".*Apidra.*", ".*Humalog.*", ".*Tresiba.*", ".*Levemir.*",
            ".*Lantus.*", ".*Insulatard.*", ".*NovoMix.*",
        ], 
        antidiabetic=True
    ),

    # -------------------------------------------------------------------------
    # GENERAL MEDICINE: CARDIOVASCULAR
    # -------------------------------------------------------------------------
    Drug("aspirin", cardiovascular=True),
    Drug("atenolol", beta_blocker=True),
    # ACE inhibitors (selected)
    Drug("lisinopril", ace_inhibitor=True),
    Drug("ramipril", ace_inhibitor=True),
    # Statins
    Drug("atorvastatin", ["Lipitor"], statin=True),
    Drug("fluvastatin", ["Lescol.*"], statin=True),
    Drug("pravastatin", ["Lipostat"], statin=True),
    Drug("rosuvastatin", ["Crestor"], statin=True),
    Drug("simvastatin", ["Zocor"], statin=True),
    Drug(["simvastatin", "ezetimibe"], ["Inegy"], statin=True),

    # -------------------------------------------------------------------------
    # GENERAL MEDICINE: RESPIRATORY
    # -------------------------------------------------------------------------
    Drug(
        "salbutamol",
        ["salbut.*", "vent.*"],
        # ... actually (CPFT 2013): salbutamol
        respiratory=True, beta_agonist=True
    ),

    # -------------------------------------------------------------------------
    # GENERAL MEDICINE: GASTROINTESTINAL
    # -------------------------------------------------------------------------
    Drug(
        "lactulose",
        ["lactul.*", "Duphal.*", "Lactug.*", "laevol.*"],
        # ... actually (CPFT 2013): lactulose
        gastrointestinal=True
    ),
    Drug("lansoprazole", proton_pump_inhibitor=True),
    Drug("omeprazole", proton_pump_inhibitor=True),
    Drug("senna", gastrointestinal=True),

    # -------------------------------------------------------------------------
    # GENERAL MEDICINE: OTHER
    # -------------------------------------------------------------------------
    Drug("ibuprofen", nonsteroidal_anti_inflammatory=True),
    Drug("levothyroxine"),
    Drug("paracetamol"),
    Drug("thiamine", vitamin=True),

    # -------------------------------------------------------------------------
    # MAYBE ADD:
    # - OPIOIDS
    # - clonidine
    # - cloral betaine
    # - ?domperidone
    # - donepezil
    # - gabapentin
    # - hyoscine
    # - Keppra = levetiracetam
    # - linezolid (as it's an MAOI)
    # - memantine
    # - methyldopa
    # - ?metoclopramide
    # - nicotine
    # - pregabalin
    # - promethazine
    # - ropinirole
    # - rotigotine
    # - selegiline
    # - topiramate
    # -------------------------------------------------------------------------

]  # type: List[Drug]


# =============================================================================
# High-speed lookup versions of the original constants
# =============================================================================

DRUGS_BY_GENERIC_NAME = {d.generic_name: d for d in DRUGS}


# =============================================================================
# Get drug object by name
# =============================================================================

def get_drug(drug_name: str,
             name_is_generic: bool = False,
             include_categories: bool = False) -> Optional[Drug]:
    """
    Converts a drug name to a :class:`.Drug` class.

    If you already have the generic name, you can get the Drug more
    efficiently by setting ``name_is_generic=True``.

    Set ``include_categories=True`` to include drug categories (such as
    tricyclics) as well as individual drugs.
    """
    drug_name = drug_name.strip().lower()
    if name_is_generic:
        drug = DRUGS_BY_GENERIC_NAME.get(drug_name)  # type: Optional[Drug]
        if drug is not None and drug.category_not_drug and not include_categories:  # noqa
            return None
        return drug
    else:
        for d in DRUGS:
            if d.name_matches(drug_name):
                return d
        return None


# =============================================================================
# Convert drug names to generic equivalents
# =============================================================================

def drug_name_to_generic(drug_name: str,
                         unknown_to_default: bool = False,
                         default: str = None,
                         include_categories: bool = False) -> str:
    """
    Converts a drug name to the name of its generic equivalent.
    """
    drug = get_drug(drug_name, include_categories=include_categories)
    if drug is not None:
        return drug.generic_name
    return default if unknown_to_default else drug_name


def drug_names_to_generic(drugs: List[str],
                          unknown_to_default: bool = False,
                          default: str = None,
                          include_categories: bool = False) -> List[str]:
    """
    Converts a list of drug names to their generic equivalents.

    The arguments are as for :func:`drug_name_to_generic` but this function
    handles a list of drug names rather than a single one.

    Note in passing the following conversion of blank-type representations from
    R via ``reticulate``, when using e.g. the ``default`` parameter and storing
    results in a ``data.table()`` character column:

    .. code-block:: none

        ------------------------------  ----------------
        To Python                       Back from Python
        ------------------------------  ----------------
        [not passed, so Python None]    "NULL"
        NULL                            "NULL"
        NA_character_                   "NA"
        NA                              TRUE (logical)
        ------------------------------  ----------------

    """
    return [
        drug_name_to_generic(drug,
                             unknown_to_default=unknown_to_default,
                             default=default,
                             include_categories=include_categories)
        for drug in drugs
    ]


# =============================================================================
# Check drugs against criteria
# =============================================================================

def drug_matches_criteria(drug: Drug, **criteria: Dict[str, bool]) -> bool:
    """
    Determines whether a drug, passed as an instance of :class:`.Drug`, matches
    the specified criteria.

    Args:
        drug: a :class:`.Drug` instance
        criteria: ``name=value`` pairs to match against the attributes of
            the :class:`Drug` class. For example, you can include keyword
            arguments like ``antidepressant=True``.
    """
    for attribute, value in criteria.items():
        if getattr(drug, attribute) != value:
            return False
    return True


def all_drugs_where(sort=True,
                    include_categories: bool = False,
                    **criteria: Dict[str, bool]) -> List[Drug]:
    """
    Find all drugs matching the specified criteria (see
    :func:`drug_matches_criteria`). If ``include_categories`` is true, then
    drug categories (like "tricyclics") are included as well as individual
    drugs.

    Pass keyword arguments such as

    .. code-block:: python

        from cardinal_pythonlib.psychiatry.drugs import *
        non_ssri_antidep = all_drugs_where(antidepressant=True, ssri=False)
        print([d.generic_name for d in non_ssri_antidep])
        conventional_antidep = all_drugs_where(conventional_antidepressant=True)
        print([d.generic_name for d in conventional_antidep])
    """
    matching_drugs = []  # type: List[Drug]
    for drug in DRUGS:
        if drug.category_not_drug and not include_categories:
            continue
        if drug_matches_criteria(drug, **criteria):
            matching_drugs.append(drug)
    if sort:
        matching_drugs.sort(key=lambda d: d.generic_name)
    return matching_drugs


def drug_name_matches_criteria(drug_name: str,
                               name_is_generic: bool = False,
                               include_categories: bool = False,
                               **criteria: Dict[str, bool]) -> bool:
    """
    Establish whether a single drug, passed by name, matches the specified
    criteria. See :func:`drug_matches_criteria`.
    """
    drug = get_drug(drug_name, name_is_generic)
    if drug is None:
        return False
    if drug.category_not_drug and not include_categories:
        return False
    return drug_matches_criteria(drug, **criteria)


def drug_names_match_criteria(drug_names: List[str],
                              names_are_generic: bool = False,
                              include_categories: bool = False,
                              **criteria: Dict[str, bool]) -> List[bool]:
    """
    Establish whether multiple drugs, passed as a list of drug names, each
    matches the specified criteria. See :func:`drug_matches_criteria`.
    """
    return [
        drug_name_matches_criteria(
            dn,
            name_is_generic=names_are_generic,
            include_categories=include_categories,
            **criteria)
        for dn in drug_names
    ]
