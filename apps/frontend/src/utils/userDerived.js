export const calculateAge = (dob) => {
    if (!dob) return "--";
    const birth = new Date(dob);
    const diff = Date.now() - birth.getTime();
    return new Date(diff).getUTCFullYear() - 1970;
};

export function calculateBMI(heightCm, weightKg) {
    if (!heightCm || !weightKg) return null;
    const h = heightCm / 100;
    return (weightKg / (h * h)).toFixed(1);
}
