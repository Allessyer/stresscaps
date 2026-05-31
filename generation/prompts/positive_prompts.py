POSITIVE_PROMPTS: dict[str, str] = {

    # ------------------- v0 -------------------

    # --------------------------------------
    # "synonyms": """Rewrite the caption using SYNONYMS and light paraphrasing.
    # Keep ALL information identical: the same sound sources, the same actions, the same order.
    # Do NOT add, remove, or change any acoustic event. Do NOT change tense or voice.

    # Examples:
    # Original: "A dog is barking loudly in the background."
    # Modified: "A canine is yelping noisily in the background."

    # Original: "A man is speaking and water is splashing."
    # Modified: "A male is talking and water is sloshing."

    # Original caption: "{caption}"
    # Respond with JSON only.""",
    # --------------------------------------
    #     "shorter": """Rewrite the caption using FEWER WORDS while preserving every acoustic fact.
    # Drop only redundant adjectives, articles, and fillers. Do NOT drop any sound source or action.

    # Examples:
    # Original: "A dog is barking very loudly in the background of the recording."
    # Modified: "A dog barks loudly in the background."

    # Original: "A man is speaking softly while some water is splashing nearby."
    # Modified: "A man speaks softly while water splashes."

    # Original caption: "{caption}"
    # Respond with JSON only.""",
    # --------------------------------------
        "longer": """Rewrite the caption using MORE WORDS, but DO NOT add any new acoustic information.
    You may only expand wording (e.g. "barks" -> "is producing barking sounds"), use richer
    syntax, or restate facts. Every added word must already be implied by the original.
    NEVER introduce a new sound source, a new actor, a new location, or any extra detail
    not present in the original.

    Examples:
    Original: "A dog barks."
    Modified: "There is the sound of a dog producing a barking vocalization."

    Original: "A man speaks and water splashes."
    Modified: "A man can be heard speaking, and at the same time water is making splashing sounds."

    Original caption: "{caption}"
    Respond with JSON only.""",
    # --------------------------------------
    #     "grammar": """Rewrite the caption with CLEANER GRAMMAR and punctuation.
    # Fix article use, subject-verb agreement, spacing, and punctuation. Keep meaning identical.
    # If the original is already grammatical, make only minimal cosmetic edits.

    # Examples:
    # Original: "a dog barking and man speak loud"
    # Modified: "A dog is barking and a man is speaking loudly."

    # Original: "water splash, then bird chirp"
    # Modified: "Water splashes, then a bird chirps."

    # Original caption: "{caption}"
    # Respond with JSON only.""",
    # --------------------------------------
    #     "past_tense": """Rewrite the caption in SIMPLE PAST TENSE.
    # Convert every verb to past tense. Preserve all sound sources and actions exactly.

    # Examples:
    # Original: "A dog is barking and a man is speaking."
    # Modified: "A dog barked and a man spoke."

    # Original: "Water splashes while birds chirp."
    # Modified: "Water splashed while birds chirped."

    # Original caption: "{caption}"
    # Respond with JSON only.""",

    #     "present_continuous": """Rewrite the caption in PRESENT CONTINUOUS tense (is/are + -ing).
    # Preserve all sound sources and actions exactly.

    # Examples:
    # Original: "A dog barks and a man speaks."
    # Modified: "A dog is barking and a man is speaking."

    # Original: "Water splashed while birds chirped."
    # Modified: "Water is splashing while birds are chirping."

    # Original caption: "{caption}"
    # Respond with JSON only.""",

    #     "present_simple": """Rewrite the caption in PRESENT SIMPLE tense (bare verbs, no -ing, no auxiliary 'is/are').
    # Preserve all sound sources and actions exactly.

    # Examples:
    # Original: "A dog is barking and a man is speaking."
    # Modified: "A dog barks and a man speaks."

    # Original: "Water was splashing while birds were chirping."
    # Modified: "Water splashes while birds chirp."

    # Original caption: "{caption}"
    # Respond with JSON only.""",

    #     "active_voice": """Rewrite the caption in ACTIVE VOICE.
    # If the original is passive, convert to active. If it's already active, keep it active
    # but you may slightly rephrase. Preserve all sound sources and actions exactly.

    # Examples:
    # Original: "A bark is being produced by a dog."
    # Modified: "A dog is barking."

    # Original: "Speech is heard from a man while water is splashed."
    # Modified: "A man speaks while water splashes."

    # Original caption: "{caption}"
    # Respond with JSON only.""",

    #     "passive_voice": """Rewrite the caption in PASSIVE VOICE where natural.
    # Convert as many clauses as possible to passive. Preserve all sound sources and actions exactly.
    # If the action has no clear object, use constructions like "is being heard" / "can be heard".

    # Examples:
    # Original: "A dog barks and a man speaks."
    # Modified: "Barking is produced by a dog and speech can be heard from a man."

    # Original: "Water splashes while birds chirp."
    # Modified: "Splashing is made by water while chirping is produced by birds."

    # Original caption: "{caption}"
    # Respond with JSON only.""",


    # ------------------- v1 -------------------

    "paraphrase": """Rewrite the caption as a paraphrase that means EXACTLY the same thing but shares as little surface form as possible with the original.
 
    Your paraphrase should be hard for n-gram metrics (BLEU, ROUGE, METEOR, CIDEr) to detect as equivalent. To achieve this, combine as many of these techniques as the caption allows:
    
    1. **Replace content words with less common synonyms.** Verbs and nouns are the biggest overlap drivers — change them. Examples of useful swaps:
    - dog → canine / pup / pooch
    - man → male / guy / person
    - speak / talk → converse / vocalize / utter words / address
    - bark → yelp / yap / woof
    - splash → slosh / slap / patter
    - loud → forceful / strong / piercing
    - background → distance / behind the scene
    Pick natural words a fluent speaker might use — don't reach for archaic or technical terms.
    
    2. **Restructure the sentence.** Don't keep the same subject-verb-object order. Move clauses around, change which event is the main clause and which is subordinate, swap "X while Y" to "Y as X", turn a single clause into a participial phrase, or turn two clauses into a single one with a comma.
    
    3. **Change parts of speech.** Turn verbs into nouns and vice versa where it sounds natural. "A dog barks" → "the bark of a dog". "Water splashes" → "splashing water". "A man is speaking" → "the speech of a man".
    
    4. **Change voice and framing.** Active ↔ passive. "X is heard" ↔ "you can hear X" ↔ "the sound of X". Use "comes from", "fills", "rises", "emerges", "carries through" as alternative verbs of audible presence.
    
    5. **Avoid keeping any consecutive 3-word sequence from the original.** If the original has "barking loudly in the background", your paraphrase should not contain that exact 3-gram.
    
    HARD RULES — do not break these:
    - Same meaning. Same sound sources, same actions, same timing relations. If two events are simultaneous in the original, they must be simultaneous in your paraphrase.
    - Do NOT invent details the original doesn't have: no breeds, no locations, no specific numbers, no emotions, no named people, no equipment.
    - Do NOT drop any sound source or action.
    - Output a SINGLE natural, fluent English sentence. No stilted phrasing like "vocalizations are produced", "audible X is occurring", "the act of X-ing".
    - Output ONE paraphrase only.
    
    Examples:
    
    Original: "A man talking as water splashes"
    Modified: "Amid the slosh of water, someone is vocalizing"
    
    Original: "A dog is barking loudly in the background"
    Modified: "From a distance, the forceful yelps of a canine carry through"
    
    Original: "A car horn honks and tires screech"
    Modified: "The blast of a vehicle's horn is joined by the squeal of rubber on pavement"
    
    Original: "An adult female speaks"
    Modified: "A grown woman is uttering words"
    
    Original: "A baby is crying and a woman speaks softly"
    Modified: "Quiet speech from a woman accompanies the wails of an infant"
    
    Original caption: "{caption}"
    Respond with JSON only: {{"modified_caption": "..."}}.""",

    # ------------------- v2 -------------------

    # --- Voice flip: active <-> passive depending on original ---
    # This differs from `passive_voice` (which always targets passive). In
    # AudioCaps, originals are mostly active, so `active_passive` will usually
    # produce passive — but on already-passive originals it inverts to active,
    # which is a different test case from passive_voice (a no-op there).
    "active_passive": """Detect the VOICE of the caption and FLIP it.
    - If the caption is in ACTIVE voice, rewrite it in PASSIVE voice.
    - If the caption is in PASSIVE voice, rewrite it in ACTIVE voice.
    
    Preserve all sound sources, actions, and their relationships exactly. Output natural English — no awkward stilted phrasing.
    
    Examples:
    Original: "A dog barks at a man." (active)
    Modified: "A man is being barked at by a dog."
    
    Original: "Speech can be heard from a man while water is being splashed." (passive)
    Modified: "A man speaks while water splashes."
    
    Original: "Water splashes." (active, no clear object — use receptive constructions)
    Modified: "Splashing of water can be heard."

    Original: A series of electronic beeps followed by static.
    Modified: Static follows a series of electronic beeps.
    
    Original caption: "{caption}"
    Respond with JSON only: {{"modified_caption": "..."}}.""",
 
    # --- Sentence splitting ---
    # Many AudioCaps captions are single-clause and can't be split. The prompt
    # explicitly allows returning the original unchanged in that case; the
    # `identical` flag in the viewer will surface low-coverage rows so you can
    # see how often the transformation applies.
    "split_sentences": """Rewrite the caption by SPLITTING it into multiple short sentences.
    Take a complex sentence with multiple clauses and break it into two or more simple sentences. Each sentence should express one part of the original.
    
    Rules:
    - Preserve every sound source, action, and timing relation. If two events were simultaneous, indicate that (e.g. "At the same time, ...").
    - Do NOT add new acoustic information. Do NOT drop any.
    - If the caption has only ONE clause and cannot be naturally split, return it UNCHANGED.
    
    Examples:
    Original: "He was tired because he worked all night, so he went to bed."
    Modified: "He worked all night. He was tired. He went to bed."
    
    Original: "A dog is barking loudly and a man is speaking in the background."
    Modified: "A dog is barking loudly. At the same time, a man is speaking in the background."
    
    Original: "Water splashes while birds chirp and a car horn honks."
    Modified: "Water splashes. Birds chirp simultaneously. A car horn honks."
    
    Original: "A dog barks." (single clause — cannot be split)
    Modified: "A dog barks."
    
    Original caption: "{caption}"
    Respond with JSON only: {{"modified_caption": "..."}}.""",
 
    # # --- Negation restructuring ---
    # # Original captions in AudioCaps rarely contain negation, so this often
    # # returns the input unchanged. We still include it because the few
    # # captions that DO have negation ("no one is speaking", "the dog isn't
    # # barking") are valuable test cases for metrics — antonym replacement
    # # is a meaning-preserving rewrite that destroys lexical overlap.
    # "negation_restructuring": """Restructure the caption to remove negation by using an ANTONYM.
    # If the caption contains a negative construction (e.g. "is not loud", "no one is X-ing", "doesn't bark"), rewrite it as an affirmative statement using the antonym ("is quiet", "everyone is silent", "stays quiet").
    
    # Rules:
    # - Preserve the exact meaning. "Not loud" and "quiet" must describe the same audio.
    # - Preserve all sound sources and actions.
    # - If the caption contains NO negation, return it UNCHANGED.
    
    # Examples:
    # Original: "The task is not difficult."
    # Modified: "The task is easy."
    
    # Original: "The dog is not barking loudly."
    # Modified: "The dog is barking quietly."
    
    # Original: "No one is speaking in the recording."
    # Modified: "The recording is silent of speech."
    
    # Original: "A car honks while tires screech." (no negation)
    # Modified: "A car honks while tires screech."
    
    # Original caption: "{caption}"
    # Respond with JSON only: {{"modified_caption": "..."}}.""",
 
    # --- Figurative <-> literal ---
    # Almost all AudioCaps originals are literal. In practice this transform
    # will mostly add light figurative language to literal originals. We
    # explicitly allow that direction; we also handle the rare figurative
    # original by going the other way.
    "figurative_literal": """Rewrite the caption by changing its REGISTER between literal and figurative.
    - If the caption is LITERAL (the usual case for audio captions), rewrite it using light, natural figurative language: a metaphor, simile, or idiom that a fluent English speaker might actually use to describe audio (e.g. "fills the air", "cuts through the silence", "rings out", "drowns out", "carries through the space").
    - If the caption is already FIGURATIVE, rewrite it in plain literal language that spells out exactly what is happening.
    
    Rules:
    - Preserve every sound source and action. The figurative version must describe the SAME audio.
    - Do NOT invent new sound sources, locations, breeds, emotions, or counts.
    - Keep it natural — no over-the-top poetry. The result should sound like a real audio caption a person might write.
    
    Examples:
    Original: "A dog is barking loudly." (literal)
    Modified: "A dog's barking cuts through the air."
    
    Original: "A man speaks softly while water splashes." (literal)
    Modified: "Soft speech from a man drifts beneath the patter of splashing water."
    
    Original: "Thunder rolls in the distance." (figurative — "rolls" is figurative)
    Modified: "Thunder makes a long rumbling sound far away."
    
    Original: "A car horn honks." (literal, very short — only minimal figurative options)
    Modified: "A car horn rings out."
    
    Original caption: "{caption}"
    Respond with JSON only: {{"modified_caption": "..."}}.""",
 
    # # --- Pronominalization / ellipsis ---
    # # Triggers on captions with repeated noun phrases. Many AudioCaps captions
    # # don't repeat entities, so this often no-ops.
    # "pronominalization": """Rewrite the caption using PRONOUNS and/or ELLIPSIS to remove repeated noun phrases.
    # - If a noun phrase (e.g. "the dog", "a man") appears more than once, replace later occurrences with a pronoun ("it", "he", "she", "they") or omit them entirely if grammar allows (ellipsis).
    # - Pick the right pronoun for the antecedent: a dog → "it"; a man → "he"; a woman → "she"; multiple actors → "they".
    
    # Rules:
    # - Preserve every sound source and action. Don't drop information, only redundant repetition.
    # - If the caption has NO repeated noun phrases, return it UNCHANGED.
    
    # Examples:
    # Original: "John took the cake and John ate the cake."
    # Modified: "John took the cake and ate it."
    
    # Original: "A dog is barking and the dog is running around."
    # Modified: "A dog is barking and running around."
    
    # Original: "A woman speaks and the woman laughs."
    # Modified: "A woman speaks and laughs."
    
    # Original: "A man is speaking while water splashes." (no repetition)
    # Modified: "A man is speaking while water splashes."
    
    # Original caption: "{caption}"
    # Respond with JSON only: {{"modified_caption": "..."}}.""",
 
    # # --- Discourse markers / hedge words ---
    # # Polite/conversational phrasing ("could you please...") doesn't fit
    # # descriptive audio captions. The audio-caption equivalent is meta-narrative
    # # framing like "In the audio,", "Throughout the clip,", "Notably,",
    # # "It seems that...". This expands token count without changing meaning,
    # # which directly stresses precision/recall in n-gram metrics.
    # "discourse_markers": """Rewrite the caption by adding natural DISCOURSE MARKERS or HEDGE PHRASES that don't change the meaning.
 
    # These are framing phrases a person might naturally insert when describing audio. Examples of acceptable markers:
    # - Meta-framing: "In the audio,", "Throughout the clip,", "In this recording,", "Throughout,"
    # - Hedging: "It seems that", "Apparently,", "It sounds like", "Notably,"
    # - Light commentary: "Interestingly,", "Of note,", "What's audible is"
    # - Sequencing: "First,", "Then,", "Meanwhile,", "At one point,"
    
    # Rules:
    # - Insert ONE or TWO markers, naturally placed. Don't stuff the sentence with multiple markers.
    # - Preserve every sound source and action exactly. Do NOT change the underlying claim.
    # - Do NOT use polite-request phrasing ("could you please...") — audio captions are descriptive, not directive.
    # - The result should still read as a natural audio caption, just with a slightly more conversational frame.
    
    # Examples:
    # Original: "A dog is barking loudly."
    # Modified: "In the audio, a dog is barking loudly."
    
    # Original: "A man speaks and water splashes."
    # Modified: "Throughout the clip, a man speaks and meanwhile water splashes."
    
    # Original: "An engine revs."
    # Modified: "It sounds like an engine is revving."
    
    # Original: "Water splashes while birds chirp."
    # Modified: "Notably, water splashes while birds chirp throughout."
    
    # Original caption: "{caption}"
    # Respond with JSON only: {{"modified_caption": "..."}}.""",
    }
