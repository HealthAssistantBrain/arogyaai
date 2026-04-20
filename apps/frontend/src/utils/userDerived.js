export function calculateAge(dob) {
    if (!dob) return null;
    const birth = new Date(dob);
    const today = new Date();

    let age = today.getFullYear() - birth.getFullYear();
    const m = today.getMonth() - birth.getMonth();

    if (m < 0 || (m === 0 && today.getDate() < birth.getDate())) {
        age--;
    }

    return age;
}

export function calculateBMI(heightCm, weightKg) {
    if (!heightCm || !weightKg) return null;
    const h = heightCm / 100;
    return (weightKg / (h * h)).toFixed(1);
}
