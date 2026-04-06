const DEFAULT_AVATAR = `data:image/svg+xml;utf8,${encodeURIComponent(
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96" fill="none">
    <rect width="96" height="96" rx="24" fill="#F3F1FF"/>
    <circle cx="48" cy="36" r="18" fill="#6143F4" fill-opacity="0.18"/>
    <path d="M22 78c4.8-13.6 16-20.4 26-20.4S69.2 64.4 74 78" fill="#6143F4" fill-opacity="0.22"/>
    <circle cx="48" cy="34" r="15" fill="#6143F4" fill-opacity="0.78"/>
  </svg>`
)}`;

const firstNonEmpty = (...values) => {
  for (const value of values) {
    if (typeof value === 'string' && value.trim()) {
      return value.trim();
    }
  }

  return '';
};

export function getUserProfile(user, _role = 'user') {
  const fullNameFromParts = [user?.first_name, user?.last_name]
    .filter((value) => typeof value === 'string' && value.trim())
    .join(' ')
    .trim();

  const name = firstNonEmpty(
    user?.profile?.full_name,
    user?.full_name,
    user?.name,
    fullNameFromParts,
    user?.username
  ) || 'User';

  const patientId = firstNonEmpty(
    user?.profile?.patient_id,
    user?.patient_id,
    user?.patientId,
    user?.patientID,
    user?.medical_id,
    user?.medicalId
  );

  const avatar = firstNonEmpty(
    user?.profile?.avatar_url,
    user?.avatar,
    user?.avatar_url,
    user?.avatarUrl,
    user?.profile_image,
    user?.profileImage,
    user?.profile_image_url,
    user?.profileImageUrl,
    user?.image_url,
    user?.imageUrl,
    user?.photo_url,
    user?.photoUrl
  ) || DEFAULT_AVATAR;

  return {
    name,
    patientId,
    avatar,
    subtitle: patientId ? `ID: ${patientId}` : '',
    fallbackAvatar: DEFAULT_AVATAR,
  };
}
