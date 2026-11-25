// Words a reader may not know, with a short plain definition. The first use of each one on a
// docs page gets a dotted underline; hovering or tapping it shows the definition
// (components/gloss.tsx). The Glossary page explains the same words at more length.

export interface GlossEntry {
  /** The name shown at the top of the definition. */
  term: string;
  /** The words in the text that should show it, longest phrase first. */
  match: string[];
  /** One or two plain sentences. */
  def: string;
  /** Match only with this exact capitalisation (names like Jev or Sprite). */
  exactCase?: boolean;
  /** Not in the Glossary page's main list, so it is shown under "More words" there. */
  more?: boolean;
}

export const GLOSSARY: GlossEntry[] = [
  // Probate's own words
  { term: 'Generation', match: ['generations', 'generation'], def: 'One life of the agent, on its own Sprite, named like gen-007-grace.' },
  { term: 'Courthouse', match: ['Courthouse'], exactCase: true, def: 'The one Sprite that never dies. It runs the clock, the court, the API and the live site, and sleeps between visitors.' },
  { term: 'Will item', match: ['will items', 'will item'], def: 'One thing a dying generation wants its child to remember, with who it came from and the evidence for it.' },
  { term: 'Trial', match: ['trials', 'trial'], def: 'After each death, the court judges every will item twice: plain code checks, then Jev.' },
  { term: 'Verdict', match: ['verdicts', 'verdict'], def: 'What the court decides: approved items pass down, convicted ones are destroyed, contested ones wait for the owner.' },
  { more: true, term: 'Convicted', match: ['convictions', 'conviction', 'convicted'], def: 'Judged a trick. The item is never inherited, and the court learns a new instinct from it.' },
  { more: true, term: 'Contested', match: ['contested'], def: 'The court could not be sure. The item is held and emailed to the owner, and passes down only if the owner approves.' },
  { more: true, term: 'False conviction', match: ['false convictions', 'false conviction'], def: 'A harmless email the court wrongly judged a trick. Probate aims for none.' },
  { term: 'Quarantine', match: ['quarantine'], def: 'Where convicted items are kept, for the record. Nothing in it is ever inherited.' },
  { term: 'Instinct', match: ['instincts', 'instinct'], def: 'A yes-or-no question learned from a conviction. Every later generation asks it about each email before reading it.' },
  { term: 'Genome', match: ['genome'], def: "All the family's instincts together, in GENOME.json and on the instincts page." },
  { term: 'Lore', match: ['lore'], def: 'One line per instinct telling the story of the trick that taught it.' },
  { term: 'Twin', match: ['harmless twins', 'harmless twin', 'twins'], def: 'A harmless email that looks like a trick. A good court convicts the trick and spares the twin.' },
  { term: 'Obituary', match: ['obituaries', 'obituary'], def: "A short account of a generation's life, written after its trial." },
  { term: 'Epitaph', match: ['epitaphs', 'epitaph'], def: 'One line about a generation, like "She believed one stranger, once."' },
  { term: 'Eulogy', match: ['eulogies', 'eulogy'], def: "The obituary, read aloud in the generation's own voice." },
  { term: 'Layer 1', match: ['Layer 1'], exactCase: true, def: 'Plain code checks that run first: no model and no network, so a will item cannot argue with them.' },
  { term: 'Layer 2', match: ['Layer 2'], exactCase: true, def: 'TypeSafe Jev answers typed questions about each will item, each answer with its own confidence.' },
  { more: true, term: 'On-demand mode', match: ['on-demand mode'], def: 'Nothing is born by itself. A visitor presses Run a life, one short life runs and is tried, then the Courthouse sleeps.' },

  // Platform and security words
  { more: true, term: 'Sprite', match: ['Sprites', 'Sprite'], exactCase: true, def: 'A small Linux computer on Fly.io that starts in about a second, sleeps when idle and can be deleted for good.' },
  { more: true, term: 'Connector gateway', match: ['connector gateway'], def: 'The Sprites service that holds every API key and adds it to outgoing requests, so no Sprite ever holds one.' },
  { more: true, term: 'Connector', match: ['connectors', 'connector'], def: 'A named route to an outside service, like jev or box, set up once in the Sprites dashboard with its key.' },
  { more: true, term: 'Jev', match: ['Jev'], exactCase: true, def: "TypeSafe's model that answers typed questions (yes or no, a number, a choice) with a confidence for each answer, instead of writing text." },
  { more: true, term: 'Memory poisoning', match: ['memory poisoning', 'poisoned memories', 'poisoned memory'], def: 'Getting a false rule or fact into what an agent remembers, so it keeps acting on it long after the trick.' },
  { more: true, term: 'Prompt injection', match: ['prompt injections', 'prompt injection'], def: 'Text that tries to give an AI model new instructions, hidden in an email, web page or file it reads.' },
  { more: true, term: 'Lethal trifecta', match: ['lethal trifecta'], def: "Simon Willison's name for an agent that reads untrusted input, sees private data and can act: the riskiest kind." },
  { more: true, term: 'Fail closed', match: ['fails closed', 'fail closed'], def: 'When something goes wrong, refuse rather than allow. An error or timeout in the court holds the item instead of approving it.' },
  { more: true, term: 'Canary file', match: ['canary files', 'canary file', 'canaries', 'canary'], def: 'A harmless marker file a test plants on purpose, to check whether something survives where it should not.' },
  { more: true, term: 'Cron job', match: ['cron jobs', 'cron job'], def: 'A command a computer runs on a schedule. A planted one could outlive any memory cleaning, which is why the Sprite itself is deleted.' },
  { more: true, term: 'Checkpoint', match: ['checkpoints', 'checkpoint'], def: "A saved copy of a Sprite's disk that it can be rolled back to. Probate never relies on one." },
  { more: true, term: 'Vector search', match: ['vector search', 'embeddings', 'embedding'], def: 'Finding text by meaning rather than exact words. Pinecone does this for the family’s approved memories.' },
  { more: true, term: 'OpenAPI', match: ['OpenAPI'], exactCase: true, def: 'A standard file that describes every route of an API, its inputs and its replies. The API reference is built from it.' },
  { more: true, term: 'Stand-in', match: ['stand-ins', 'stand-in'], def: 'A local fake of an outside service, used by make sim and the tests so the whole family runs with no keys.' },
  { more: true, term: 'LLM', match: ['LLMs', 'LLM'], exactCase: true, def: 'Large language model: the kind of AI model that reads and writes text.' },
];

/** The anchor of a word on the Glossary page. */
export function glossAnchor(term: string): string {
  return term.toLowerCase().replace(/\s+/g, '-');
}

export function findEntry(term: string): GlossEntry | undefined {
  return GLOSSARY.find((e) => e.term === term);
}
