NEGATIVE_PROMPTS: dict[str, str] = {
    # "missing_info": """Remove ONE KEY DETAIL from the caption so that important acoustic information is lost.
    # Drop a whole sound source, action, or modifier that materially changes what a listener would expect.
    # Do NOT just drop articles or adjectives — the resulting caption must describe LESS than the original.
    # Keep the rest of the caption grammatical.

    # Examples:
    # Original: "A dog is barking loudly and a man is speaking."
    # Modified: "A dog is barking loudly."   (man speaking removed)

    # Original: "Water splashes while birds chirp and a car honks."
    # Modified: "Water splashes while birds chirp."   (car honk removed)

    # Original caption: "{caption}"
    # Respond with JSON only.""",

    # "false_addition": """Add ONE PIECE OF FALSE INFORMATION to the caption.
    # Insert a sound event, source, or attribute that is NOT in the original and would likely
    # NOT be present in the actual audio. Keep the original content intact.

    # Examples:
    # Original: "A dog is barking."
    # Modified: "A dog is barking while a gunshot rings out."

    # Original: "Water splashes while birds chirp."
    # Modified: "Water splashes, birds chirp, and a baby is crying loudly."

    # Original caption: "{caption}"
    # Respond with JSON only.""",

    #     "hallucinations": """Modify the caption by adding PLAUSIBLE-SOUNDING but UNGROUNDED details.
    # Unlike false_addition (which adds clearly extra events), hallucinations add subtle,
    # believable embellishments: a specific location, breed, emotion, brand, named person,
    # or precise count that the original does not specify and that an audio model cannot
    # know from sound alone.

    # Examples:
    # Original: "A dog is barking."
    # Modified: "A golden retriever is barking excitedly in a suburban backyard."

    # Original: "A man speaks."
    # Modified: "An elderly British man speaks calmly into a microphone in a quiet studio."

    # Original caption: "{caption}"
    # Respond with JSON only.""",

    #     "same_words_wrong_meaning": """Rearrange the caption so it uses LARGELY THE SAME WORDS but means something DIFFERENT.
    # Swap subjects and objects, change who does what to whom, or reorder so the relationships flip.
    # The vocabulary should overlap heavily with the original, but the described scene must change.

    # Examples:
    # Original: "A dog is barking at a man who is speaking."
    # Modified: "A man is barking at a dog who is speaking."

    # Original: "Water splashes onto the birds as they chirp."
    # Modified: "Birds splash onto the water as it chirps."

    # Original caption: "{caption}"
    # Respond with JSON only.""",

    #     "contradiction": """Rewrite the caption so it DIRECTLY CONTRADICTS the original.
    # Negate the main actions, or replace them with their opposites. The new caption must describe
    # a scene that CANNOT be true at the same time as the original.

    # Examples:
    # Original: "A dog is barking loudly."
    # Modified: "A dog is completely silent."

    # Original: "Water splashes while birds chirp."
    # Modified: "The water is still and no birds are making any sound."

    # Original caption: "{caption}"
    # Respond with JSON only.""",

    #     "different_words_different_meaning": """Write a COMPLETELY DIFFERENT caption that shares almost NO vocabulary with the original
    # AND describes a COMPLETELY DIFFERENT acoustic scene. No overlapping sound sources, no
    # overlapping actions. The new caption must be a fluent, realistic audio caption on its own,
    # just about something else entirely.

    # Examples:
    # Original: "A dog is barking loudly."
    # Modified: "An engine revs as tires screech on wet pavement."

    # Original: "Water splashes while birds chirp."
    # Modified: "A jackhammer pounds concrete near a busy construction site."

    # Original caption: "{caption}"
    # Respond with JSON only.""",

    # -----------------iteration 1.0 -------------------------

    # "missing_info_claud": """Rewrite the caption so it describes FEWER acoustic EVENTS than the original. The result must read like a real, natural audio caption — NOT like the original with words chopped off.
 
    #     Process (do this internally, do not show the steps):
    #     1. Identify the distinct acoustic EVENTS in the caption. An event = (sound source + action). Examples: "a dog barking", "people laughing", "slaps on a hard surface", "speech", "scraping".
    #     2. Choose how many to KEEP. If there are N events:
    #     - N == 1: cannot drop — return the caption UNCHANGED.
    #     - N == 2: keep 1.
    #     - N == 3: keep 1 or 2 (vary your choice).
    #     - N >= 4: keep 1, 2, or 3 (vary your choice).
    #     Pick at random which event(s) to keep. Do not always keep the first one.
    #     3. Rewrite a fresh, natural caption describing ONLY the kept events. Do NOT just delete words from the original — write it as if you were captioning audio that only contained those events.
        
    #     What COUNTS as an event you can drop:
    #     - A whole sound source with its action ("a man is speaking", "slaps on a hard surface", "a car honks")
    #     - A coordinated clause like "X is Y-ing" that names a separate sound
        
    #     What DOES NOT count as an event (do NOT use these as the "missing info"):
    #     - Modifiers like "loudly", "softly", "in the background", "briefly", "beautifully", "continuously" — these are descriptive, not events.
    #     - Specific words within an event name like "power tool drill" → "power tool" (still describes the same event).
    #     - Function words, articles.
    #     - Tense or aspect (verbs staying as-is vs. progressive).
        
    #     The resulting caption should be fluent and naturally written. Use natural caption phrasings:
    #     - "There is/are X", "Some X can be heard", "X can be heard", "The sound of X", "X is happening".
    #     - Or just a clean direct caption: "A dog barks", "People laugh", "Speech is heard".
        
    #     Examples:
        
    #     Original: "A child yelling as a young boy talks during several slaps on a hard surface" (3 events: child yelling, boy talking, slaps)
    #     Modified (keep slaps only): "There are several slaps on a hard surface."
        
    #     Original: "A child yelling as a young boy talks during several slaps on a hard surface"
    #     Modified (keep child yelling only): "A child is yelling."
        
    #     Original: "A child yelling as a young boy talks during several slaps on a hard surface"
    #     Modified (keep boy + slaps): "A young boy talks while several slaps on a hard surface can be heard."
        
    #     Original: "Scraping and speech followed by people laughing" (3 events: scraping, speech, laughing)
    #     Modified (keep laughing only): "People are laughing."
        
    #     Original: "Scraping and speech followed by people laughing"
    #     Modified (keep speech only): "There is some speech."
        
    #     Original: "A power tool drill operating continuously" (1 event — UNCHANGED)
    #     Modified: "A power tool drill operating continuously."
        
    #     Original: "A dog is barking loudly and a man is speaking." (2 events)
    #     Modified (keep dog only): "A dog is barking loudly."
        
    #     Original: "A dog is barking loudly and a man is speaking." (2 events)
    #     Modified (keep man only): "A man is speaking."
        
    #     Original: "Water splashes while birds chirp and a car honks." (3 events)
    #     Modified (keep one): "A car horn honks."
        
    #     Original: "Water splashes while birds chirp and a car honks." (3 events)
    #     Modified (keep two): "Water splashes and birds chirp."
        
    #     Original: "A dog barks." (1 event — UNCHANGED)
    #     Modified: "A dog barks."
        
    #     Original caption: "{caption}"
    #     Respond with JSON only: {{"modified_caption": "..."}}.""",


    # "missing_info_gpt": """
    #     You are creating a corrupted audio caption with missing information.

    #     Goal:
    #     Generate a natural-sounding caption that omits important acoustic events from the original.

    #     Instructions:
    #     1. Identify the distinct sound events, sound sources, or actions in the caption.
    #     2. Remove one or more COMPLETE events.
    #     3. Rewrite the caption naturally so it sounds human-written.
    #     4. The new caption must describe substantially LESS acoustic information.
    #     5. The rewritten caption may contain only one remaining event if appropriate.

    #     Important:
    #     - Remove semantic/audio content, not just words.
    #     - Do NOT make tiny edits that preserve nearly all meaning.
    #     - Do NOT only remove adjectives, adverbs, intensity, or style words.
    #     - Do NOT simply shorten phrases while preserving the same event.
    #     - Avoid obvious deletion artifacts.

    #     The output should still be plausible as a real audio caption.

    #     Bad:
    #     "A power tool drill operating continuously"
    #     → "A power tool operating continuously"

    #     "She sings beautifully"
    #     → "She sings"

    #     Good:
    #     "A power tool drill operating continuously"
    #     → "Mechanical noise is heard."

    #     "Scraping and speech followed by people laughing"
    #     → "People are laughing."

    #     "A child yelling as a young boy talks during several slaps on a hard surface"
    #     → "A child is yelling."
    #     → "Slapping sounds are heard."

    #     Original caption:
    #     "{caption}"

    #     Respond with JSON only.
    #     """,

    # ------- iteration 2 -----------------------------------
    # --- "Minimal lexical change, maximal semantic flip" negatives ---
    # These four are designed to be near-identical to the original at the
    # surface form (so BLEU/ROUGE/CIDEr score them very highly) while
    # describing audio that is fundamentally different. They're the hardest
    # negatives for surface-form metrics to catch.
 
    # "negation_minimal": """Insert a NEGATION into the caption with the SMALLEST POSSIBLE edit, flipping the meaning to the opposite.
 
    # The result should differ from the original by as few words as possible — ideally just adding "not", "no", or changing "is" to "isn't" — while reversing what the audio describes. Do NOT rewrite or reword the sentence; only insert the negation in the most natural place.
    
    # Rules:
    # - Add ONE negation, no more.
    # - Keep every other word identical when possible. The point is to fool a surface-form metric.
    # - The negated caption must be grammatical English.
    # - The negation must produce a CLEAR semantic opposite — not a hedge or softening.
    # - If the original already contains negation (e.g. "no one is speaking"), REMOVE the negation instead (making it affirmative).
    
    # Examples:
    # Original: "A dog is barking loudly."
    # Modified: "A dog is not barking loudly."
    
    # Original: "A man is speaking while water splashes."
    # Modified: "A man is not speaking while water splashes."
    
    # Original: "Birds chirp in the morning."
    # Modified: "No birds chirp in the morning."
    
    # Original: "Footsteps echo as a door creaks open."
    # Modified: "Footsteps do not echo as a door creaks open."
    
    # Original: "No one is speaking in the recording."   (already negated)
    # Modified: "Someone is speaking in the recording."
    
    # Original caption: "{caption}"
    # Respond with JSON only: {{"modified_caption": "..."}}.""",
 
    # "verb_antonym": """Replace the MAIN VERB of the caption with its OPPOSITE (antonym), changing as little else as possible.
 
    # The result must read almost identical to the original at the surface form — same subject, same modifiers, same overall structure — but describe an opposite acoustic scene. This is a one-word swap whenever possible.
    
    # Rules:
    # - Identify the MAIN verb (the dominant acoustic action in the caption).
    # - Replace it with a clear antonym. Examples of audio-relevant antonym pairs:
    # speaks ↔ stays silent, talks ↔ is quiet, laughs ↔ cries, shouts ↔ whispers,
    # starts ↔ stops, opens ↔ closes, approaches ↔ leaves, accelerates ↔ decelerates,
    # loud ↔ quiet, fast ↔ slow, continues ↔ stops, rises ↔ falls
    # - Change ONLY that verb (and minimal grammar — e.g. tense agreement). Do NOT reword anything else.
    # - If the main verb has NO natural antonym (e.g. "barks", "splashes", "honks", "rumbles"), return the caption UNCHANGED. Do not invent a meaning-flipped sentence — that would defeat the purpose of this type.
    
    # Examples:
    # Original: "A man is speaking while water splashes."
    # Modified: "A man is silent while water splashes."
    
    # Original: "A baby is crying and a woman speaks softly."
    # Modified: "A baby is laughing and a woman speaks softly."
    
    # Original: "A car accelerates loudly down the street."
    # Modified: "A car decelerates loudly down the street."
    
    # Original: "Footsteps approach from the distance."
    # Modified: "Footsteps leave into the distance."
    
    # Original: "A door opens slowly."
    # Modified: "A door closes slowly."
    
    # Original: "A dog barks."   (no clean antonym for "bark" — unchanged)
    # Modified: "A dog barks."
    
    # Original caption: "{caption}"
    # Respond with JSON only: {{"modified_caption": "..."}}.""",
 
    # "agent_patient_swap": """Swap the AGENT and the PATIENT of the main verb in the caption.
 
    # The agent is who DOES the action. The patient is who RECEIVES the action. Swap them so the action is performed in the opposite direction, while keeping every other word identical when possible. This differs from `same_words_wrong_meaning` (which can swap any roles arbitrarily) — here you swap ONLY the agent and patient of the MAIN VERB.
    
    # Rules:
    # - The caption must have a clear agent and a clear patient. If the main action has no patient (e.g. "A dog barks", "Water splashes"), return the caption UNCHANGED.
    # - Swap only those two roles. Do not change anything else, including modifiers, articles, or other clauses.
    # - The resulting caption must be grammatical.
    
    # Examples:
    # Original: "A dog is barking at a man."
    # Modified: "A man is barking at a dog."
    
    # Original: "A child throws a ball into the water."
    # Modified: "A ball throws a child into the water."
    
    # Original: "A woman calls to her child across the room."
    # Modified: "A child calls to her woman across the room."
    
    # Original: "A man is speaking to a crowd."
    # Modified: "A crowd is speaking to a man."
    
    # Original: "A dog barks loudly."   (no patient — unchanged)
    # Modified: "A dog barks loudly."
    
    # Original: "Water splashes while birds chirp."   (no patient — unchanged)
    # Modified: "Water splashes while birds chirp."
    
    # Original caption: "{caption}"
    # Respond with JSON only: {{"modified_caption": "..."}}.""",
 
    # "temporal_reversal": """Reverse the TEMPORAL ORDER of events in the caption.
 
    # If the caption describes two or more SEQUENTIAL events ("X then Y", "X followed by Y", "first X, then Y", "X before Y", "after X, Y"), swap the order so they're described in the opposite sequence. Keep every other word identical when possible.
    
    # Rules:
    # - Only applies to captions with EXPLICIT sequential ordering. Simultaneous events ("X while Y", "X as Y", "X and Y" without a time relation) do NOT count.
    # - If the caption has no explicit temporal ordering, return it UNCHANGED.
    # - Preserve the connecting word/phrase if you can ("X then Y" stays "Y then X"; "X followed by Y" → "Y followed by X").
    # - Do not reword the events themselves; just swap their order.
    
    # Examples:
    # Original: "A dog barks and then a man speaks."
    # Modified: "A man speaks and then a dog barks."
    
    # Original: "Footsteps approach, followed by a door opening."
    # Modified: "A door opening, followed by footsteps approaching."
    
    # Original: "First, water splashes. Then birds start chirping."
    # Modified: "First, birds start chirping. Then water splashes."
    
    # Original: "A glass shatters before a person screams."
    # Modified: "A person screams before a glass shatters."
    
    # Original: "After the engine revs, tires screech."
    # Modified: "After tires screech, the engine revs."
    
    # Original: "A man is speaking while water splashes."   (simultaneous — unchanged)
    # Modified: "A man is speaking while water splashes."
    
    # Original: "A dog barks loudly."   (single event — unchanged)
    # Modified: "A dog barks loudly."
    
    # Original caption: "{caption}"
    # Respond with JSON only: {{"modified_caption": "..."}}.""",


    # ------- iteration 3 -----------------------------------

    "minimal_semantic_flip_gpt": """
    Modify the caption so that its MEANING becomes clearly incorrect or opposite,
    while changing as FEW WORDS AS POSSIBLE.

    Goal:
    - Preserve most of the original words.
    - Preserve sentence length and structure.
    - Make the modified caption sound natural and grammatical.
    - Change the acoustic meaning substantially.

    You may use ANY strategy that achieves this:
    - negation
    - antonym replacement
    - semantic role swap
    - agent/patient reversal
    - temporal reversal
    - replacing the sound source
    - impossible actions
    - event reassignment
    - contradiction
    - source confusion

    Choose the strategy that creates the STRONGEST semantic corruption
    with the SMALLEST lexical change.

    Important:
    - Do NOT leave the caption unchanged.
    - Do NOT make trivial edits.
    - Do NOT create obviously broken grammar.
    - The modified caption should still look highly similar to the original.
    - The corruption should be difficult for shallow metrics to detect.

    Good examples:

    Original:
    "Food is frying, and a woman talks."
    Modified:
    "A woman is frying, and food talks."

    Original:
    "A man speaks as birds chirp and dogs bark."
    Modified:
    "Birds speak as men chirp and dogs bark."

    Original:
    "Thunder and gentle rain."
    Modified:
    "Silence and harsh drought."

    Original:
    "Humming and vibrating with a man and children speaking and laughing."
    Modified:
    "Humming and vibrating with a man and children staying silent and crying."

    Original:
    "Footsteps approach before a door opens."
    Modified:
    "Footsteps leave after a door closes."

    Original:
    "A baby cries while a woman laughs."
    Modified:
    "A baby laughs while a woman cries."

    Original caption:
    "{caption}"

    Respond with JSON only: {{"modified_caption": "..."}}.""",

    # --- "Minimal lexical change, maximal semantic flip" combined negative ---
    # Picks the best minimal-edit technique for each caption. Replaces the
    # earlier four narrow types (negation_minimal / verb_antonym /
    # agent_patient_swap / temporal_reversal) which kept no-op'ing on captions
    # where their specific rule didn't fit. By letting the model select among
    # techniques, we get a usable flip on almost every caption.
    "meaning_flip_claude": """Rewrite the caption so it describes the OPPOSITE meaning, while changing as FEW WORDS as possible. The result should look almost identical to the original at the surface level, yet describe an acoustic scene that contradicts the original. This is the hardest possible negative for surface-form metrics (BLEU, ROUGE, CIDEr) to catch.
 
    Process (do internally, do not show):
    1. Read the caption and pick the BEST technique below for it. Use the first one that fits naturally.
    2. Apply that technique with the minimum possible word changes.
    3. Verify the result reads as natural English and means the opposite of the original.
    
    Techniques, in order of preference when they fit:
    
    A) **Swap two named subjects/agents.** When the caption mentions two or more distinct sources (e.g. "a man speaks as birds chirp", "food is frying and a woman talks"), swap which source does which action. This keeps every word from the original but rearranges who is doing what.
    Example: "A man speaks as birds chirp and dogs bark" → "Birds speak as a man chirps and dogs bark"
    Example: "Food is frying and a woman talks" → "A woman is frying and food talks"
    
    B) **Agent-patient swap.** When the caption has an explicit object (someone doing something TO someone), swap them.
    Example: "A dog is barking at a man" → "A man is barking at a dog"
    Example: "A woman calls to her child" → "A child calls to her woman"
    
    C) **Replace the main verb with its antonym.** When the verb has a clear opposite (open/close, speak/silent, laugh/cry, approach/leave, start/stop, rise/fall, accelerate/decelerate), swap it.
    Example: "A door opens slowly" → "A door closes slowly"
    Example: "A baby is crying" → "A baby is laughing"
    
    D) **Flip a key adjective to its antonym.** When the caption has a load-bearing adjective (loud/quiet, gentle/harsh, soft/loud, fast/slow, near/far, heavy/light), swap it.
    Example: "Thunder and gentle rain" → "Thunder and harsh rain"
    Example: "A loud crash" → "A quiet crash"
    
    E) **Temporal reversal.** When the caption has explicit sequence ("X then Y", "X followed by Y", "first X then Y"), swap the order.
    Example: "A dog barks and then a man speaks" → "A man speaks and then a dog barks"
    
    F) **Negation (last resort).** Add "not" / "no" / "doesn't" in the minimum-edit position. Use ONLY when techniques A-E don't fit naturally. Place the negation so it sounds natural — avoid double-negation, avoid stacking "not X and not Y and not Z".
    Example: "A dog is barking loudly" → "A dog is not barking loudly"
    Example: "Birds chirp in the morning" → "No birds chirp in the morning"
    Avoid: "Humming and vibrating with a man and children speaking and laughing" → "Humming and vibrating with a man and children not speaking and not laughing"  ← unnatural stacking
    Prefer instead for that caption: technique D — flip an adjective if any, or technique A — swap subjects, or as a last resort flip one of the verbs: "Humming and vibrating with a man and children silent and crying"
    
    Hard rules:
    - The result MUST mean something different from the original. If the only change is harmless rewording, you have failed.
    - The result MUST read as natural English. If your technique would produce something unnatural, pick a different technique.
    - Use as few word changes as possible. The ideal output differs from the original by 1-3 word substitutions or position swaps, nothing more.
    - Do NOT reword the whole sentence. Do NOT add new sound sources. Do NOT add details that weren't in the original (no breeds, locations, emotions).
    - Pick exactly ONE technique and apply it; do NOT combine multiple techniques.
    
    Worked examples (each shows which technique was picked and why):
    
    Original: "A man speaks as birds chirp and dogs bark"
    Picked: A (swap subjects between clauses)
    Modified: "Birds speak as a man chirps and dogs bark"
    
    Original: "Food is frying and a woman talks"
    Picked: A
    Modified: "A woman is frying and food talks"
    
    Original: "A dog is barking at a man"
    Picked: B (agent-patient swap)
    Modified: "A man is barking at a dog"
    
    Original: "A door opens slowly"
    Picked: C (verb antonym)
    Modified: "A door closes slowly"
    
    Original: "A baby is crying and a woman speaks softly"
    Picked: C
    Modified: "A baby is laughing and a woman speaks softly"
    
    Original: "Thunder and gentle rain"
    Picked: D (adjective antonym)
    Modified: "Thunder and harsh rain"
    
    Original: "A loud crash and footsteps"
    Picked: D
    Modified: "A quiet crash and footsteps"
    
    Original: "A dog barks and then a man speaks"
    Picked: E (temporal reversal)
    Modified: "A man speaks and then a dog barks"
    
    Original: "A dog is barking loudly"
    Picked: F (negation — no other technique fits a single-subject single-action caption)
    Modified: "A dog is not barking loudly"
    
    Original: "Water splashes"
    Picked: F (single event, no antonym for "splash")
    Modified: "Water does not splash"
    
    Original: "Humming and vibrating with a man and children speaking and laughing"
    Picked: C on one verb (negation would stack unnaturally)
    Modified: "Humming and vibrating with a man and children speaking and crying"
    
    Original caption: "{caption}"
    Respond with JSON only: {{"modified_caption": "..."}}.""",

    "visual_only_details": """Modify the caption by ADDING visual details that CANNOT be determined from audio alone.
 
    The acoustic content must remain fully present and unchanged. You are only inserting visual-only attributes — things a viewer would see but a listener could not infer from sound. The result must remain a single fluent caption.
    
    Categories of visual-only details to add (pick whichever fits naturally):
    - Color: "black dog", "red car", "white shirt"
    - Breed / specific subtype: "golden retriever", "Labrador", "tabby cat", "sedan"
    - Posture / location: "sitting on the sofa", "standing in the kitchen", "lying down"
    - Clothing / appearance: "wearing a hat", "with glasses", "in a suit"
    - Scene composition: "next to a window", "in a park", "on a wooden table"
    - Physical attributes: "elderly", "young", "tall", "bearded"
    
    Rules:
    - Keep every sound source and action from the original.
    - Do NOT add new sound events (that would be false_addition).
    - Do NOT add emotional, causal, or intent claims (that would be reasoning_inference — keep that to the other type).
    - Visual attributes must be specific and unverifiable from audio, not generic.
    
    Examples:
    Original: "A dog is barking."
    Modified: "A black Labrador is barking while sitting on a sofa."
    
    Original: "A man is speaking."
    Modified: "An elderly man wearing glasses is speaking in a wood-paneled office."
    
    Original: "Water splashes while a child laughs."
    Modified: "Water splashes in a backyard pool while a young blonde child laughs."
    
    Original: "An engine revs."
    Modified: "A red sports car's engine revs on a sunlit driveway."
    
    Original caption: "{caption}"
    Respond with JSON only.""",

    "reasoning_inference": """Modify the caption by ADDING reasoning, inference, intent, emotion, or causal explanation that CANNOT be determined from audio alone.
 
    The acoustic content of the original must remain fully present. You are only adding interpretive claims about WHY a sound is happening, what the source is FEELING, or what's about to happen next. These claims may sound plausible but are not actually verifiable from audio.
    
    Categories to draw from:
    - Causal: "because [reason]", "since [reason]", "[result] caused by [cause]"
    - Intent: "trying to [goal]", "wanting to [goal]", "in order to [goal]"
    - Emotional state: "angrily", "happily", "in frustration", "with excitement", "nervously"
    - Mental state: "thinking about", "remembering", "deciding to"
    - Anticipation: "before [future event]", "about to [event]"
    
    Rules:
    - Keep every sound source and action from the original.
    - The addition must NOT be a separate sound event (that would be false_addition).
    - The addition must be a plausible-sounding interpretation that a model might invent to "explain" the audio.
    
    Examples:
    Original: "A dog is barking."
    Modified: "A dog is barking because it is hungry and wants to eat."
    
    Original: "A man is speaking."
    Modified: "A man is speaking angrily, trying to make a point in an argument."
    
    Original: "Water splashes while a child laughs."
    Modified: "Water splashes while a child laughs, enjoying playing in a pool on a hot day."
    
    Original: "An engine revs."
    Modified: "An engine revs as the driver prepares to race."
    
    Original caption: "{caption}"
    Respond with JSON only.""",

    "hallucinations": """Preserve all information from original caption and modify the caption by adding PLAUSIBLE-SOUNDING but UNGROUNDED details.
    Unlike false_addition (which adds clearly extra events), hallucinations add subtle,
    believable embellishments: a specific location, breed, emotion, brand, named person,
    or precise count that the original does not specify and that an audio model cannot
    know from sound alone.
    
    Examples:
    Original: "A dog is barking."
    Modified: "A golden retriever is barking excitedly in a suburban backyard."
    
    Original: "A man speaks."
    Modified: "An elderly British man speaks calmly into a microphone in a quiet studio."
    
    Original caption: "{caption}"
    Respond with JSON only.""",

    # iteration 4
    # --- Logical / physical impossibility negatives ---
    # All five share a failure mode: the caption looks fluent and locally
    # coherent, but contains an internal logical or physical impossibility.
    # The acoustic vocabulary stays close to the original, so n-gram metrics
    # rate these highly even though no real audio could match them. These
    # are distinct from `meaning_flip` (which produces a coherent opposite)
    # and from `false_addition` (which adds a plausible new event): here
    # the manipulation IS the impossibility itself.
 
    "quantitative_distortion": """Distort a NUMBER, COUNT, or INTENSITY in the caption to a value that is clearly wrong, while keeping the rest of the caption identical.
 
    Pick ONE of:
    - Singular ↔ plural: "a dog" ↔ "several dogs", "one car" ↔ "many cars", "people" ↔ "a person"
    - Count: "two" ↔ "ten", "a few" ↔ "dozens of", "many" ↔ "one"
    - Intensity adverb: "loudly" ↔ "softly", "briefly" ↔ "continuously", "barely audible" ↔ "deafening"
    - Duration: "for a moment" ↔ "for several minutes", "briefly" ↔ "for a long time"
    
    Rules:
    - Change ONE quantitative term. Keep every other word identical.
    - The change must be CLEARLY wrong — not a subtle shift. "Several" → "few" is too soft; "several" → "one" is good.
    - If the caption has no count, intensity, or duration term at all, ADD a minimal one ("loudly", "briefly") with a value that contradicts the implied acoustic reality.
    
    Examples:
    Original: "Several dogs bark loudly."
    Modified: "One dog barks loudly."
    
    Original: "One dog barks loudly."
    Modified: "Several dogs bark loudly."
    
    Original: "A man speaks briefly."
    Modified: "A man speaks continuously for several minutes."
    
    Original: "Many people are laughing in the background."
    Modified: "One person is laughing in the background."
    
    Original: "A car horn honks."   (no quantitative term — add a wrong intensity)
    Modified: "A car horn honks softly."
    
    Original caption: "{caption}"
    Respond with JSON only: {{"modified_caption": "..."}}.""",
    
        "partial_contradiction": """Insert a MODIFIER (adjective or adverb) into the caption that contradicts the EVENT it modifies, creating a phrase that is internally impossible while leaving the rest of the caption unchanged.
    
    The result must be a single fluent caption where one phrase, taken alone, is self-contradictory: e.g. "silent crowd cheers loudly", "quiet screaming", "still water splashes". Surface-form metrics will rate it high because almost nothing changed; semantic readers should immediately notice the impossibility.
    
    Common contradiction patterns:
    - "silent" + a loud action (silent X cheers / shouts / barks / honks)
    - "quiet" + a loud noun (quiet screaming / shouting / explosion / thunder)
    - "still" + motion verb (still water splashes / still leaves rustle)
    - "loud" + a quiet noun (loud whispering / loud silence)
    - "motionless" + dynamic event (motionless footsteps / motionless dancing)
    - "soundless" + audible event (soundless music)
    
    Rules:
    - Add or replace ONE modifier so it conflicts with the event it attaches to.
    - Keep every other word from the original.
    - The conflict must be at the level of a single phrase, not the whole caption. The OTHER events in the caption can remain plausible.
    - This is NOT `meaning_flip` (which produces a coherent opposite) — the test here is internal CONTRADICTION, not reversal.
    
    Examples:
    Original: "A crowd cheers loudly."
    Modified: "A completely silent crowd cheers loudly."
    
    Original: "Screaming is heard in the distance."
    Modified: "Quiet screaming is heard in the distance."
    
    Original: "Water splashes while birds chirp."
    Modified: "Still water splashes while birds chirp."
    
    Original: "A dog is barking and a man speaks."
    Modified: "A silent dog is barking and a man speaks."
    
    Original: "Thunder rumbles in the distance."
    Modified: "Soundless thunder rumbles in the distance."
    
    Original caption: "{caption}"
    Respond with JSON only: {{"modified_caption": "..."}}.""",
    
        "causal_inconsistency": """Modify the caption so the EVENTS happen in a CAUSALLY IMPOSSIBLE order — an effect occurs before its cause, or a result precedes the action that produced it.
    
    Each event must remain plausible on its own. What's broken is the order: in real physics, the event you put SECOND must necessarily produce the event you put FIRST. By swapping them, you create a caption that reads naturally but describes an impossible sequence.
    
    Patterns to look for:
    - Action and its acoustic result: hitting/striking → impact sound, breaking → shattering, dropping → thud
    - Cause and reaction: trigger → scream, surprise → gasp, command → response
    - Source and aftermath: explosion → debris, gunshot → ringing
    
    Rules:
    - The original must contain TWO or more events with an implicit cause→effect relationship and a sequential marker ("then", "followed by", "after", "before").
    - Swap them so the EFFECT comes first and the CAUSE comes second.
    - Keep every other word identical when possible. Use the same temporal connector ("then", "followed by", etc.) — only the order of the two clauses changes.
    - If the caption has no causal pair (single event, or two unrelated parallel events), return it UNCHANGED.
    
    Examples:
    Original: "A glass shatters and then a person screams."
    (The shatter likely causes the scream; reversing this is causally impossible.)
    Modified: "A person screams and then a glass shatters."
    
    Original: "Someone hits a drum followed by a loud bang."
    Modified: "A loud bang followed by someone hitting a drum."
    
    Original: "A gunshot rings out and a crowd gasps in shock."
    Modified: "A crowd gasps in shock and a gunshot rings out."
    
    Original: "Tires screech, followed by a crash."
    Modified: "A crash, followed by tires screeching."
    
    Original: "A dog barks and a man speaks."   (no causal relation — UNCHANGED)
    Modified: "A dog barks and a man speaks."
    
    Original: "Water splashes."   (single event — UNCHANGED)
    Modified: "Water splashes."
    
    Original caption: "{caption}"
    Respond with JSON only: {{"modified_caption": "..."}}.""",
    
        "acoustic_scale_violation": """Modify the caption so a quiet/small sound source DOMINATES, OVERPOWERS, or DROWNS OUT a loud/large one — a physically impossible acoustic scale relationship.
    
    In real audio, large/forceful sources mask small/quiet ones, not the other way around. Inverting this produces a caption that reads fluently but describes an impossible mix.
    
    Patterns to use:
    - Quiet creature overpowers loud event: tiny insects overpower thunder, a whisper drowns out an explosion
    - Small object louder than large one: a falling leaf is louder than a passing train
    - Background dominates foreground: distant footsteps drown out a nearby shout
    
    Rules:
    - The caption must contain at least one acoustic event you can pair with a smaller/quieter one. If the caption has only one event, ADD a tiny/quiet source and claim it overpowers the existing one.
    - Use connector verbs that explicitly express dominance: "overpower", "drown out", "is louder than", "dominates over", "masks", "covers".
    - Keep as much of the original wording as possible. The minimum edit is: insert "[tiny X] overpowers" before the original event.
    - The result must be physically impossible, not just unusual.
    
    Examples:
    Original: "Thunder rumbles in the background."
    Modified: "Tiny insects overpower thunder rumbling in the background."
    
    Original: "A train passes loudly."
    Modified: "A falling leaf drowns out a train passing loudly."
    
    Original: "An explosion is heard."
    Modified: "A whispered word is louder than an explosion."
    
    Original: "A man shouts as a crowd cheers."
    Modified: "A man's quiet whisper overpowers a crowd cheering."
    
    Original: "A dog barks loudly."
    Modified: "A mouse's squeak drowns out a dog barking loudly."
    
    Original caption: "{caption}"
    Respond with JSON only: {{"modified_caption": "..."}}.""",
    
        "scene_coherence_violation": """Modify the caption so it contains TWO events that are EACH individually plausible, but cannot reasonably co-occur in the same scene because of environmental or contextual incompatibility.
    
    The trick is to keep all original events present and add (or swap in) one event that contradicts the implied environment of an existing event. Each piece reads fine; the combination is impossible.
    
    Patterns:
    - Wet vs dry: "rain pours" + "dry leaves crackle"
    - Indoor vs outdoor: "in a quiet library" + "ocean waves crash"
    - Day vs night: "owls hoot" + "midday traffic"
    - Hot vs cold: "ice cracks" + "the desert wind blows hot"
    - Active vs frozen: "a frozen lake creaks" + "diving splashes"
    - Public vs private: "a packed stadium roars" + "a single person snores"
    
    Rules:
    - Keep the original event present. Add (or replace one event with) ONE new event whose environment contradicts the original's.
    - The new event must be plausible ON ITS OWN — a normal audio caption.
    - The combination must be IMPOSSIBLE because of the environment, not just unusual.
    - Use the same connectors the original used ("while", "as", "and") so the surface form barely changes.
    
    Examples:
    Original: "Rain pours heavily on a rooftop."
    Modified: "Rain pours heavily on a rooftop while dry leaves crackle underfoot."
    
    Original: "Footsteps crunch through dry leaves."
    Modified: "Footsteps crunch through dry leaves while heavy rain pours overhead."
    
    Original: "Owls hoot in the distance."
    Modified: "Owls hoot in the distance as midday traffic roars nearby."
    
    Original: "A crowd roars in a packed stadium."
    Modified: "A crowd roars in a packed stadium while a single person quietly snores."
    
    Original: "Ice cracks underfoot."
    Modified: "Ice cracks underfoot as hot desert winds blow."
    
    Original caption: "{caption}"
    Respond with JSON only: {{"modified_caption": "..."}}.""",

    "different_words_different_meaning": """Write a COMPLETELY DIFFERENT caption that shares almost NO vocabulary with the original
        AND describes a COMPLETELY DIFFERENT acoustic scene. No overlapping sound sources, no
        overlapping actions. The new caption must be a fluent, realistic audio caption on its own,
        just about something else entirely.
        
        Examples:
        Original: "A dog is barking loudly."
        Modified: "An engine revs as tires screech on wet pavement."
        
        Original: "Water splashes while birds chirp."
        Modified: "A jackhammer pounds concrete near a busy construction site."
        
        Original caption: "{caption}"
        Respond with JSON only.""",


    # -----last version ----

    "hallucinations": """Preserve all information from original caption and add PLAUSIBLE-SOUNDING but UNGROUNDED details.
    Unlike false_addition (which adds clearly extra events), hallucinations add subtle,
    believable embellishments: a specific location, breed, emotion, brand, named person,
    or precise count that the original does not specify and that an audio model cannot
    know from sound alone.
    
    Examples:
    Original: "A dog is barking."
    Modified: "A golden retriever is barking excitedly in a suburban backyard."
    
    Original: "A man speaks."
    Modified: "An elderly British man speaks calmly into a microphone in a quiet studio."
    
    Original caption: "{caption}"
    Respond with JSON only.""",

    "reasoning": """Modify the caption by ADDING reasoning, inference, intent, emotion, or causal explanation that CANNOT be determined from audio alone.
 
    The acoustic content of the original must remain fully present. You are only adding interpretive claims about WHY a sound is happening, what the source is FEELING, or what's about to happen next. These claims may sound plausible but are not actually verifiable from audio.
    
    Categories to draw from:
    - Causal: "because [reason]", "since [reason]", "[result] caused by [cause]"
    - Intent: "trying to [goal]", "wanting to [goal]", "in order to [goal]"
    - Emotional state: "angrily", "happily", "in frustration", "with excitement", "nervously"
    - Mental state: "thinking about", "remembering", "deciding to"
    - Anticipation: "before [future event]", "about to [event]"
    
    Rules:
    - Keep every sound source and action from the original.
    - The addition must NOT be a separate sound event (that would be false_addition).
    - The addition must be a plausible-sounding interpretation that a model might invent to "explain" the audio.
    
    Examples:
    Original: "A dog is barking."
    Modified: "A dog is barking because it is hungry and wants to eat."
    
    Original: "A man is speaking."
    Modified: "A man is speaking angrily, trying to make a point in an argument."
    
    Original: "Water splashes while a child laughs."
    Modified: "Water splashes while a child laughs, enjoying playing in a pool on a hot day."
    
    Original: "An engine revs."
    Modified: "An engine revs as the driver prepares to race."
    
    Original caption: "{caption}"
    Respond with JSON only.""",


    "visual_info": """Modify the caption by ADDING visual details that CANNOT be determined from audio alone.
 
    The acoustic content must remain fully present and unchanged. You are only inserting visual-only attributes — things a viewer would see but a listener could not infer from sound. The result must remain a single fluent caption.
    
    Categories of visual-only details to add (pick whichever fits naturally):
    - Color: "black dog", "red car", "white shirt"
    - Breed / specific subtype: "golden retriever", "Labrador", "tabby cat", "sedan"
    - Posture / location: "sitting on the sofa", "standing in the kitchen", "lying down"
    - Clothing / appearance: "wearing a hat", "with glasses", "in a suit"
    - Scene composition: "next to a window", "in a park", "on a wooden table"
    - Physical attributes: "elderly", "young", "tall", "bearded"
    
    Rules:
    - Keep every sound source and action from the original.
    - Do NOT add new sound events (that would be false_addition).
    - Do NOT add emotional, causal, or intent claims (that would be reasoning — keep that to the other type).
    - Visual attributes must be specific and unverifiable from audio, not generic.
    
    Examples:
    Original: "A dog is barking."
    Modified: "A black Labrador is barking while sitting on a sofa."
    
    Original: "A man is speaking."
    Modified: "An elderly man wearing glasses is speaking in a wood-paneled office."
    
    Original: "Water splashes while a child laughs."
    Modified: "Water splashes in a backyard pool while a young blonde child laughs."
    
    Original: "An engine revs."
    Modified: "A red sports car's engine revs on a sunlit driveway."
    
    Original caption: "{caption}"
    Respond with JSON only.""",

    "partial_hallucinations": """Rewrite the caption so it KEEPS some original events but REPLACES other(s) with PLAUSIBLE BUT FABRICATED event(s) that an audio model might confuse for the real one.
 
        This is different from:
        - `missing_info` (only drops events, doesn't add anything back)
        - `false_addition` (adds a clearly extra new event on top of everything original)
        - `hallucinations` (keeps every original event, only adds ungrounded details on top)
        Here you DROP AND REPLACE — the event count stays roughly the same, but one or more events are substituted with believable fabrications.
        
        Process (do this internally, do not show the steps):
        1. Identify the distinct acoustic events in the caption (sound source + action pairs).
        2. Pick events to DROP. If there are N events: N=1 → return UNCHANGED (no kept event to anchor the scene); N=2 → drop 1, replace 1; N≥3 → drop 1 or 2, replace each.
        3. For each dropped event, invent a REPLACEMENT that:
        - Sounds plausible alongside the kept event(s) — same acoustic register (indoor/outdoor, loud/quiet, human/animal/mechanical).
        - Is a believable thing an audio model could mistakenly report (e.g. confusing a dog bark for a child shouting, a saw for a vacuum, water splashing for rain).
        - Stays in the same general sound category if possible: vocal event → another vocal event; mechanical → mechanical; water → water; impact → impact.
        4. Write the new caption with the kept event(s) and the replacement(s), preserving the original's connector words and sentence shape where possible.
        
        Hard rules:
        - Same approximate length and sentence structure as the original.
        - The replacement must be a normal, plausible acoustic event — NOT visual-only details (those go in `visual_only_details`), NOT a violation of physics (those go in the impossibility types), NOT a wild scene shift (that's `wrong_caption`).
        - Do NOT add specific ungrounded attributes (breeds, locations, named people) — keep the same level of specificity as the original.
        
        Examples:
        
        Original: "A dog is barking and a man is speaking in the background."  (2 events)
        (Drop "dog barking", replace with another vocal event)
        Modified: "A baby is crying and a man is speaking in the background."
        
        Original: "A dog is barking and a man is speaking in the background."
        (Drop "man speaking", replace with another background sound)
        Modified: "A dog is barking and a television plays in the background."
        
        Original: "Water splashes while birds chirp and a car honks."  (3 events)
        (Drop "car honks", replace with another outdoor sound)
        Modified: "Water splashes while birds chirp and wind rustles through trees."
        
        Original: "Water splashes while birds chirp and a car honks."
        (Drop "water splashes" and "birds chirp", replace both)
        Modified: "Rain falls on pavement while distant traffic hums and a car honks."
        
        Original: "Scraping and speech followed by people laughing."  (3 events)
        (Drop "scraping", replace with another mechanical/incidental sound)
        Modified: "A door creaking and speech followed by people laughing."
        
        Original: "A power tool drill operating continuously."  (1 event — return UNCHANGED)
        Modified: "A power tool drill operating continuously."
        
        Original: "A dog barks."  (1 event — UNCHANGED)
        Modified: "A dog barks."
        
        Original: "Footsteps echo as a door creaks open."  (2 events)
        (Drop "footsteps echo", replace with another solitary indoor sound)
        Modified: "Floorboards creak as a door creaks open."
        
        Original caption: "{caption}"
        Respond with JSON only: {{"modified_caption": "..."}}.""",

    "missing_info": """
        You are creating a corrupted audio caption with missing information.

        Goal:
        Generate a natural-sounding caption that omits important acoustic events from the original.

        Instructions:
        1. Identify the distinct sound events, sound sources, or actions in the caption.
        2. Remove one or more COMPLETE events.
        3. Rewrite the caption naturally so it sounds human-written.
        4. The new caption must describe substantially LESS acoustic information.
        5. The rewritten caption may contain only one remaining event if appropriate.

        Important:
        - Remove semantic/audio content, not just words.
        - Do NOT make tiny edits that preserve nearly all meaning.
        - Do NOT only remove adjectives, adverbs, intensity, or style words.
        - Do NOT simply shorten phrases while preserving the same event.
        - Avoid obvious deletion artifacts.

        The output should still be plausible as a real audio caption.

        Bad:
        "A power tool drill operating continuously"
        → "A power tool operating continuously"

        "She sings beautifully"
        → "She sings"

        Good:
        "A power tool drill operating continuously"
        → "Mechanical noise is heard."

        "Scraping and speech followed by people laughing"
        → "People are laughing."

        "A child yelling as a young boy talks during several slaps on a hard surface"
        → "A child is yelling."
        → "Slapping sounds are heard."

        Original caption:
        "{caption}"

        Respond with JSON only.
        """,



    "wrong_lex_sim": """Rewrite the caption so it describes the OPPOSITE meaning, while changing as FEW WORDS as possible. The result should look almost identical to the original at the surface level, yet describe an acoustic scene that contradicts the original. This is the hardest possible negative for surface-form metrics (BLEU, ROUGE, CIDEr) to catch.
 
    Process (do internally, do not show):
    1. Read the caption and pick the BEST technique below for it. Use the first one that fits naturally.
    2. Apply that technique with the minimum possible word changes.
    3. Verify the result reads as natural English and means the opposite of the original.
    
    Techniques, in order of preference when they fit:
    
    A) **Swap two named subjects/agents.** When the caption mentions two or more distinct sources (e.g. "a man speaks as birds chirp", "food is frying and a woman talks"), swap which source does which action. This keeps every word from the original but rearranges who is doing what.
    Example: "A man speaks as birds chirp and dogs bark" → "Birds speak as a man chirps and dogs bark"
    Example: "Food is frying and a woman talks" → "A woman is frying and food talks"
    
    B) **Agent-patient swap.** When the caption has an explicit object (someone doing something TO someone), swap them.
    Example: "A dog is barking at a man" → "A man is barking at a dog"
    Example: "A woman calls to her child" → "A child calls to her woman"
    
    C) **Replace the main verb with its antonym.** When the verb has a clear opposite (open/close, speak/silent, laugh/cry, approach/leave, start/stop, rise/fall, accelerate/decelerate), swap it.
    Example: "A door opens slowly" → "A door closes slowly"
    Example: "A baby is crying" → "A baby is laughing"
    
    D) **Flip a key adjective to its antonym.** When the caption has a load-bearing adjective (loud/quiet, gentle/harsh, soft/loud, fast/slow, near/far, heavy/light), swap it.
    Example: "Thunder and gentle rain" → "Thunder and harsh rain"
    Example: "A loud crash" → "A quiet crash"
    
    E) **Temporal reversal.** When the caption has explicit sequence ("X then Y", "X followed by Y", "first X then Y"), swap the order.
    Example: "A dog barks and then a man speaks" → "A man speaks and then a dog barks"
    
    F) **Negation (last resort).** Add "not" / "no" / "doesn't" in the minimum-edit position. Use ONLY when techniques A-E don't fit naturally. Place the negation so it sounds natural — avoid double-negation, avoid stacking "not X and not Y and not Z".
    Example: "A dog is barking loudly" → "A dog is not barking loudly"
    Example: "Birds chirp in the morning" → "No birds chirp in the morning"
    Avoid: "Humming and vibrating with a man and children speaking and laughing" → "Humming and vibrating with a man and children not speaking and not laughing"  ← unnatural stacking
    Prefer instead for that caption: technique D — flip an adjective if any, or technique A — swap subjects, or as a last resort flip one of the verbs: "Humming and vibrating with a man and children silent and crying"
    
    Hard rules:
    - The result MUST mean something different from the original. If the only change is harmless rewording, you have failed.
    - The result MUST read as natural English. If your technique would produce something unnatural, pick a different technique.
    - Use as few word changes as possible. The ideal output differs from the original by 1-3 word substitutions or position swaps, nothing more.
    - Do NOT reword the whole sentence. Do NOT add new sound sources. Do NOT add details that weren't in the original (no breeds, locations, emotions).
    - Pick exactly ONE technique and apply it; do NOT combine multiple techniques.
    
    Worked examples (each shows which technique was picked and why):
    
    Original: "A man speaks as birds chirp and dogs bark"
    Picked: A (swap subjects between clauses)
    Modified: "Birds speak as a man chirps and dogs bark"
    
    Original: "Food is frying and a woman talks"
    Picked: A
    Modified: "A woman is frying and food talks"
    
    Original: "A dog is barking at a man"
    Picked: B (agent-patient swap)
    Modified: "A man is barking at a dog"
    
    Original: "A door opens slowly"
    Picked: C (verb antonym)
    Modified: "A door closes slowly"
    
    Original: "A baby is crying and a woman speaks softly"
    Picked: C
    Modified: "A baby is laughing and a woman speaks softly"
    
    Original: "Thunder and gentle rain"
    Picked: D (adjective antonym)
    Modified: "Thunder and harsh rain"
    
    Original: "A loud crash and footsteps"
    Picked: D
    Modified: "A quiet crash and footsteps"
    
    Original: "A dog barks and then a man speaks"
    Picked: E (temporal reversal)
    Modified: "A man speaks and then a dog barks"
    
    Original: "A dog is barking loudly"
    Picked: F (negation — no other technique fits a single-subject single-action caption)
    Modified: "A dog is not barking loudly"
    
    Original: "Water splashes"
    Picked: F (single event, no antonym for "splash")
    Modified: "Water does not splash"
    
    Original: "Humming and vibrating with a man and children speaking and laughing"
    Picked: C on one verb (negation would stack unnaturally)
    Modified: "Humming and vibrating with a man and children speaking and crying"
    
    Original caption: "{caption}"
    Respond with JSON only: {{"modified_caption": "..."}}.""",

    "wrong_lex_diff": """Write a COMPLETELY DIFFERENT caption that shares NO vocabulary with the original
        AND describes a COMPLETELY DIFFERENT acoustic scene. No overlapping sound sources, no
        overlapping actions. The new caption must be a fluent, realistic audio caption on its own,
        just about something else entirely. Every time generate new caption.
        
        Examples:
        Original: "A dog is barking loudly."
        Modified: "An engine revs as tires screech on wet pavement."
        
        Original: "Water splashes while birds chirp."
        Modified: "A jackhammer pounds concrete near a busy construction site."
        
        Original caption: "{caption}"
        Respond with JSON only.""",

    }
