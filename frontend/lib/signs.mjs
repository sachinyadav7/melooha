export const SIGNS = [
  "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
  "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
];

// North Indian charts print the sign number (Aries = 1) inside each house.
export function signNumber(sign) {
  return SIGNS.indexOf(sign) + 1;
}
