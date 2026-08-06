/**
 * How the gender someone picks constrains the avatar.
 *
 * Open Peeps has one `head` component holding 48 hairstyles and a separate
 * `facialHair` component with its own probability. So gender is expressed by
 * narrowing the hairstyle pool and setting the odds of facial hair, using the
 * same style throughout, which is what keeps the wall looking like one set.
 *
 * These are hairstyles that commonly read as feminine or masculine, not a claim
 * about anyone. Anybody who does not want to be sorted picks "rather not say"
 * and gets the full pool.
 *
 * Option names verified against the style definition, not guessed. `@dicebear/core`
 * validates options and throws on an unknown key, so a typo here fails loudly at
 * request time rather than quietly producing an ungendered avatar.
 */
export type Gender = "female" | "male" | "neutral";

export const GENDERS: readonly Gender[] = ["female", "male", "neutral"];

export function asGender(value: unknown): Gender {
  return GENDERS.includes(value as Gender) ? (value as Gender) : "neutral";
}

// Long, styled, tied up.
const FEMININE_HAIR = [
  "afro", "bangs", "bangs2", "bantuKnots", "bun", "bun2", "buns",
  "cornrows", "cornrows2", "grayBun", "hijab", "long", "longAfro",
  "longBangs", "longCurly", "medium1", "medium2", "medium3",
  "mediumBangs", "mediumBangs2", "mediumBangs3", "mediumStraight",
  "twists", "twists2",
];

// Short, shaved, flat, covered.
const MASCULINE_HAIR = [
  "dreads1", "dreads2", "flatTop", "flatTopLong", "grayMedium", "grayShort",
  "hatBeanie", "hatHip", "mohawk", "mohawk2", "noHair1", "noHair2", "noHair3",
  "pomp", "shaved1", "shaved2", "shaved3", "short1", "short2", "short3",
  "short4", "short5", "turban",
];

export const GENDER_OPTIONS: Record<Gender, Record<string, unknown>> = {
  female: { headVariant: FEMININE_HAIR, facialHairProbability: 0 },
  male: { headVariant: MASCULINE_HAIR, facialHairProbability: 40 },
  // Everything the style offers, including the variants left out of both lists.
  neutral: {},
};
