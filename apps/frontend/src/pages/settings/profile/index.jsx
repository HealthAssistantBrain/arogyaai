import { useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import { useAuthStore } from '../../../store/authStore';
import { useUserStore } from '../../../store/userStore';
import { getUserProfile } from '../../../lib/userProfile';
import {
    User, Ruler, Scale, Droplet, AlertTriangle, Calendar, Phone, Mail, Pencil, CheckCircle2
} from 'lucide-react';
import api from '../../../lib/axios';
import { calculateAge, calculateBMI } from '../../../utils/userDerived';

const getInitials = (name) => {
    if (!name) return "NA";
    return name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2);
};

const SettingsProfile = () => {
    const { role, profile, healthProfile, fetchProfile, profileLoading, token } = useAuthStore();
    const { user } = useUserStore();
    const profileRecord = (profile && Object.keys(profile).length > 0)
        ? profile
        : ((healthProfile && Object.keys(healthProfile).length > 0) ? healthProfile : null);
    const profileData = getUserProfile({ ...user, profile: profileRecord }, role);
    const hasLoadedProfile = Boolean(profileRecord || (user && Object.keys(user).length > 0));

    const initials = getInitials(user?.name || user?.full_name);
    const dob = user?.dob;
    const bmi = calculateBMI(user?.height, user?.weight);

    const [gender, setGender] = useState(profileRecord?.gender || '');

    const [isEditing, setIsEditing] = useState(false);
    const [email, setEmail] = useState(user?.email || "");
    const [editForm, setEditForm] = useState({
        full_name: '', phone_number: '', date_of_birth: '', height_cm: '', weight_kg: '', blood_group: '', allergies: ''
    });

    const displayDob = isEditing && editForm.date_of_birth ? editForm.date_of_birth : dob;

    const age = calculateAge(displayDob);

    useEffect(() => {
        if (token) {
            fetchProfile();
        }
    }, [fetchProfile, token]);

    if (!user) return <div className="flex h-64 items-center justify-center text-sm font-bold text-slate-500">Loading...</div>;

    if (profileLoading && !hasLoadedProfile) {
        return (
            <div className="flex h-64 items-center justify-center text-sm font-bold text-slate-500">
                Loading profile...
            </div>
        );
    }

    const handleSaveProfile = async () => {
        if (!editForm.full_name) {
            return toast.error("Name is required");
        }

        const h = Number(editForm.height_cm);
        const w = Number(editForm.weight_kg);

        if (editForm.height_cm && (isNaN(h) || h < 50 || h > 300)) {
            return toast.error("Height must be between 50 and 300 cm");
        }
        if (editForm.weight_kg && (isNaN(w) || w < 20 || w > 300)) {
            return toast.error("Weight must be between 20 and 300 kg");
        }

        const validBloodGroups = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-', ''];
        if (editForm.blood_group && !validBloodGroups.includes(editForm.blood_group)) {
            return toast.error("Invalid blood group");
        }

        const sanitizedAllergies = editForm.allergies.replace(/[<>]/g, '');

        const payload = {
            full_name: editForm.full_name,
            phone: editForm.phone_number,
            date_of_birth: editForm.date_of_birth,
            height: editForm.height_cm ? Number(editForm.height_cm) : null,
            weight: editForm.weight_kg ? Number(editForm.weight_kg) : null,
            gender: gender,
            blood_group: editForm.blood_group,
            allergies: sanitizedAllergies
        };

        console.log("Payload sent:", payload);

        try {
            const res = await api.put("/user/profile", payload);
            console.log("Response received:", res.data);

            const updatedData = res.data?.data || res.data || {};

            // 1. SAFE STATE UPDATE (CRITICAL FIX)
            useUserStore.getState().setUser((prev) => ({
                ...prev,
                ...updatedData
            }));

            // 6. SYNC WITH BACKEND & FORCE REFRESH (VERY IMPORTANT)
            const refreshProfile = async () => {
                const refreshRes = await api.get("/user/profile");
                const freshData = refreshRes.data?.data || refreshRes.data || {};
                useUserStore.getState().setUser((prev) => ({
                    ...prev,
                    ...freshData
                }));
            };

            await refreshProfile();

            setIsEditing(false);
            toast.success("Profile saved successfully");
        } catch (error) {
            console.error("Save profile error:", error);
            toast.error("Unable to save profile right now");
        }
    };

    const healthStats = [
        { id: 'height', icon: Ruler, iconColor: 'text-[#6143f4]', label: 'Height', bg: 'bg-[#6143f4]/5', suffix: 'cm' },
        { id: 'weight', icon: Scale, iconColor: 'text-[#009cde]', label: 'Weight', bg: 'bg-[#009cde]/5', suffix: 'kg' },
        { id: 'blood_group', icon: Droplet, iconColor: 'text-rose-500', label: 'Blood Type', bg: 'bg-rose-500/5', suffix: '' },
        { id: 'allergies', icon: AlertTriangle, iconColor: 'text-amber-500', label: 'Allergies', bg: 'bg-amber-500/5', small: true, suffix: '' },
    ];

    return (
        <div className="max-w-6xl mx-auto space-y-12 pb-16">
            {/* Page Header */}
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-8 pb-4 border-b border-[#6143f4]/5">
                <div className="space-y-4">
                    <h2 className="text-5xl font-black text-[#13082a] dark:text-white tracking-tighter uppercase italic leading-none">User Profile</h2>
                    <p className="text-lg text-slate-500 dark:text-slate-400 font-bold uppercase tracking-tight opacity-80 leading-none">Manage your identity and health records securely.</p>
                </div>
                <button onClick={handleSaveProfile} disabled={profileLoading} className="bg-[#6143f4] disabled:opacity-50 hover:bg-[#4a34c1] text-white px-10 py-5 rounded-[1.5rem] font-black text-xs uppercase tracking-[0.2em] shadow-2xl shadow-[#6143f4]/30 transition-all flex items-center gap-4 active:scale-95 leading-none">
                    Save Profile Changes
                </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-12">
                {/* Left Column — Profile Visual & Health Summary (4 cols) */}
                <div className="lg:col-span-4 space-y-10">

                    {/* Avatar/Identity Card */}
                    <div className="bg-white dark:bg-[#131022] rounded-[3.5rem] p-10 shadow-[0_40px_80px_-20px_rgba(97,67,244,0.1)] border border-[#6143f4]/5 flex flex-col items-center group/card">
                        <div className="relative group/avatar">
                            <div className="size-44 rounded-full border-4 border-white dark:border-white/10 p-1 bg-gradient-to-br from-[#6143f4]/20 to-transparent shadow-2xl overflow-hidden transition-transform duration-500 flex items-center justify-center">
                                <div className="w-[100px] h-[100px] rounded-full bg-gradient-to-br from-[#6C5CE7] to-[#8E7CFF] flex items-center justify-center text-white text-[28px] font-semibold">
                                    {initials.toUpperCase()}
                                </div>
                            </div>
                        </div>
                        <div className="text-center mt-8 space-y-2">
                            <h3 className="text-3xl font-black text-[#13082a] dark:text-white tracking-tighter uppercase italic leading-none">{profileData.name}</h3>
                            <p className="text-slate-400 font-black text-xs uppercase tracking-[0.25em]">{profileData.subtitle}</p>
                            <p className="text-[#6143f4] font-black text-sm uppercase tracking-widest mt-2">{bmi ? `${bmi} BMI` : "—"}</p>
                        </div>
                    </div>

                    {/* Health Stats Dashboard Summary */}
                    <div className="bg-white dark:bg-[#131022] rounded-[3.5rem] p-10 shadow-sm border border-[#6143f4]/5 space-y-8">
                        <div className="flex items-center justify-between gap-4">
                            <div className="flex items-center gap-4">
                                <div className="size-1.5 bg-[#6143f4] rounded-full"></div>
                                <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] leading-none">Health DNA Stats</h4>
                            </div>
                            {!isEditing ? (
                                <button onClick={() => {
                                    setEditForm({
                                        full_name: profileRecord?.full_name || user?.full_name || '',
                                        phone_number: profileRecord?.phone_number || profileRecord?.phone || user?.phone || '',
                                        date_of_birth: profileRecord?.date_of_birth || profileRecord?.dob || user?.dob || user?.date_of_birth || '',
                                        height_cm: profileRecord?.height_cm || profileRecord?.height || user?.height || '',
                                        weight_kg: profileRecord?.weight_kg || profileRecord?.weight || user?.weight || '',
                                        blood_group: profileRecord?.blood_group || user?.blood_group || '',
                                        allergies: profileRecord?.allergies || user?.allergies || ''
                                    });
                                    if (profileRecord?.gender || user?.gender) setGender(profileRecord?.gender || user?.gender);
                                    setIsEditing(true);
                                }} className="text-[#6143f4] active:scale-95 text-[10px] font-black uppercase tracking-[0.2em] border border-[#6143f4]/20 hover:bg-[#6143f4]/10 px-4 py-2 rounded-full transition-all flex items-center gap-2">
                                    <Pencil size={12} /> Edit
                                </button>
                            ) : (
                                <div className="flex items-center gap-2">
                                    <button onClick={() => {
                                        setEditForm({
                                            full_name: profileRecord?.full_name || user?.full_name || '',
                                            phone_number: profileRecord?.phone_number || profileRecord?.phone || user?.phone || '',
                                            date_of_birth: profileRecord?.date_of_birth || profileRecord?.dob || user?.dob || user?.date_of_birth || '',
                                            height_cm: profileRecord?.height_cm || profileRecord?.height || user?.height || '',
                                            weight_kg: profileRecord?.weight_kg || profileRecord?.weight || user?.weight || '',
                                            blood_group: profileRecord?.blood_group || user?.blood_group || '',
                                            allergies: profileRecord?.allergies || user?.allergies || '',
                                        });
                                        setGender(profileRecord?.gender || user?.gender || '');
                                        setIsEditing(false);
                                    }} className="text-slate-400 text-[10px] font-black uppercase tracking-[0.2em] border border-slate-200 dark:border-white/10 hover:bg-slate-50 dark:hover:bg-white/5 active:scale-95 px-4 py-2 rounded-full transition-all">
                                        Cancel
                                    </button>
                                    <button onClick={handleSaveProfile} disabled={profileLoading} className="text-[#6143f4] text-[10px] font-black uppercase tracking-[0.2em] border border-[#6143f4]/20 bg-[#6143f4]/10 hover:bg-[#6143f4]/20 active:scale-95 px-4 py-2 rounded-full transition-all">
                                        Save
                                    </button>
                                </div>
                            )}
                        </div>
                        <div className="grid grid-cols-2 gap-5">
                            {healthStats.map((stat) => (
                                <div key={stat.label} className={`p-6 rounded-[2.5rem] ${stat.bg} border border-[#6143f4]/5 hover:scale-105 transition-transform duration-300 group shadow-sm relative`}>
                                    <stat.icon size={22} className={`${stat.iconColor} mb-4 group-hover:scale-110 transition-transform`} strokeWidth={2.5} />
                                    <p className="text-[9px] text-slate-500 uppercase font-black tracking-[0.2em] leading-none">{stat.label}</p>

                                    {isEditing ? (
                                        stat.id === 'blood_group' ? (
                                            <div className="mt-2 text-sm text-[#13082a] dark:text-white font-black">
                                                <select
                                                    value={editForm[stat.id]}
                                                    onChange={(e) => setEditForm({ ...editForm, blood_group: e.target.value })}
                                                    className="w-full bg-transparent border-b border-[#6143f4]/30 focus:outline-none focus:border-[#6143f4] text-[#13082a] dark:text-white font-black text-xs md:text-sm pb-1 uppercase tracking-tighter"
                                                >
                                                    <option value="">-</option>
                                                    <option value="A+">A+</option>
                                                    <option value="A-">A-</option>
                                                    <option value="B+">B+</option>
                                                    <option value="B-">B-</option>
                                                    <option value="AB+">AB+</option>
                                                    <option value="AB-">AB-</option>
                                                    <option value="O+">O+</option>
                                                    <option value="O-">O-</option>
                                                </select>
                                            </div>
                                        ) : (
                                            <div className="flex items-center mt-2 group">
                                                <input
                                                    type={stat.id === 'allergies' ? "text" : "number"}
                                                    value={editForm[stat.id === 'height' ? 'height_cm' : stat.id === 'weight' ? 'weight_kg' : stat.id]}
                                                    onChange={(e) => setEditForm({ ...editForm, [stat.id === 'height' ? 'height_cm' : stat.id === 'weight' ? 'weight_kg' : stat.id]: e.target.value })}
                                                    className="w-full bg-transparent border-b border-[#6143f4]/30 focus:outline-none focus:border-[#6143f4] text-[#13082a] dark:text-white font-black text-xs md:text-sm pb-1 placeholder:text-slate-300"
                                                    placeholder={`Enter ${stat.label}`}
                                                />
                                                {stat.suffix && <span className="ml-1 text-xs text-[#13082a] dark:text-white font-black italic">{stat.suffix}</span>}
                                            </div>
                                        )
                                    ) : (
                                        <>
                                            {stat.id === 'height' ? (
                                                <p className={`font-black text-[#13082a] dark:text-white mt-2 leading-none italic text-xl md:text-2xl uppercase tracking-tighter`}>
                                                    {user?.height ? `${user.height} cm` : "--"}
                                                </p>
                                            ) : stat.id === 'weight' ? (
                                                <p className={`font-black text-[#13082a] dark:text-white mt-2 leading-none italic text-xl md:text-2xl uppercase tracking-tighter`}>
                                                    {user?.weight ? `${user.weight} kg` : "--"}
                                                </p>
                                            ) : (
                                                <p className={`font-black text-[#13082a] dark:text-white mt-2 leading-none italic ${stat.small && String(user?.[stat.id] ?? profileRecord?.[stat.id] ?? healthProfile?.[stat.id] ?? '').length > 10 ? 'text-xs' : 'text-xl md:text-2xl uppercase tracking-tighter'}`}>
                                                    {(user?.[stat.id] ?? profileRecord?.[stat.id] ?? healthProfile?.[stat.id]) ? `${user?.[stat.id] ?? profileRecord?.[stat.id] ?? healthProfile?.[stat.id]} ` : '-- '}
                                                    {(user?.[stat.id] ?? profileRecord?.[stat.id] ?? healthProfile?.[stat.id]) && stat.suffix && <span className="text-sm tracking-normal not-italic opacity-60 ml-1">{stat.suffix}</span>}
                                                </p>
                                            )}
                                        </>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                {/* Right Column — Detailed Forms & Preferences (8 cols) */}
                <div className="lg:col-span-8 space-y-12">
                    {/* Personal Information Form Card */}
                    <div className="bg-white dark:bg-[#131022] rounded-[4rem] shadow-sm border border-[#6143f4]/5 overflow-hidden">
                        <div className="px-10 py-8 border-b border-slate-50 dark:border-white/5 flex flex-col md:flex-row md:items-center justify-between gap-6">
                            <div className="flex items-center gap-5">
                                <div className="size-12 bg-[#6143f4]/10 rounded-2xl flex items-center justify-center text-[#6143f4] shadow-inner border border-[#6143f4]/10">
                                    <User size={24} strokeWidth={2.5} />
                                </div>
                                <h3 className="text-2xl font-black text-[#13082a] dark:text-white tracking-tighter uppercase italic leading-none mt-1">Personal Identity</h3>
                            </div>
                            <div className="flex items-center gap-4 px-6 py-2.5 bg-emerald-500/10 border border-emerald-500/10 rounded-full shadow-sm leading-none self-start md:self-auto">
                                <div className="size-2 rounded-full bg-emerald-500 animate-pulse"></div>
                                <span className="text-[9px] font-black text-emerald-600 dark:text-emerald-400 uppercase tracking-[0.25em] mt-0.5">AES-256 Encrypted</span>
                            </div>
                        </div>

                        <div className="p-10 lg:p-12 space-y-12">
                            {/* Form Grid */}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
                                <div className="space-y-4">
                                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] ml-2 leading-none">Full Legal Name</label>
                                    <div className="relative group">
                                        <User className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-300 group-focus-within:text-[#6143f4] transition-colors" size={18} />
                                        <input className="w-full pl-14 pr-6 py-5 bg-slate-50 dark:bg-white/5 border border-transparent rounded-[1.5rem] focus:ring-4 focus:ring-[#6143f4]/10 focus:border-[#6143f4]/20 text-sm text-[#13082a] dark:text-white font-black uppercase tracking-tight transition-all disabled:opacity-70 disabled:cursor-not-allowed" value={isEditing ? editForm.full_name : (profileRecord?.full_name || user?.full_name || '')} onChange={(e) => setEditForm({ ...editForm, full_name: e.target.value })} disabled={!isEditing} type="text" />
                                    </div>
                                </div>
                                <div className="space-y-4">
                                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] ml-2 leading-none">Secure Email Address</label>
                                    <div className="relative group">
                                        <Mail className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-300 group-focus-within:text-[#6143f4] transition-colors" size={18} />
                                        <input className="w-full pl-14 pr-6 py-5 bg-slate-50 dark:bg-white/5 border border-transparent rounded-[1.5rem] focus:ring-4 focus:ring-[#6143f4]/10 focus:border-[#6143f4]/20 text-sm text-[#13082a] dark:text-white font-black tracking-tight transition-all disabled:opacity-70 disabled:cursor-not-allowed" value={isEditing ? email : (user?.email || "No email")} onChange={(e) => setEmail(e.target.value)} disabled={!isEditing} type="email" />
                                    </div>
                                </div>
                                <div className="space-y-4">
                                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] ml-2 leading-none">Mobile Intel Line</label>
                                    <div className="relative group">
                                        <Phone className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-300 group-focus-within:text-[#6143f4] transition-colors" size={18} />
                                        <input className="w-full pl-14 pr-6 py-5 bg-slate-50 dark:bg-white/5 border border-transparent rounded-[1.5rem] focus:ring-4 focus:ring-[#6143f4]/10 focus:border-[#6143f4]/20 text-sm text-[#13082a] dark:text-white font-black uppercase tracking-tight transition-all disabled:opacity-70 disabled:cursor-not-allowed" value={isEditing ? editForm.phone_number : (profileRecord?.phone_number || profileRecord?.phone || user?.phone || '')} onChange={(e) => setEditForm({ ...editForm, phone_number: e.target.value })} disabled={!isEditing} type="text" />
                                    </div>
                                </div>
                                <div className="space-y-4">
                                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] ml-2 leading-none">Chronological Birth</label>
                                    <div className="relative group">
                                        <Calendar className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-300 group-focus-within:text-[#6143f4] transition-colors" size={18} />
                                        {isEditing ? (
                                            <input className="w-full pl-14 pr-6 py-5 bg-slate-50 dark:bg-white/5 border border-transparent rounded-[1.5rem] focus:ring-4 focus:ring-[#6143f4]/10 focus:border-[#6143f4]/20 text-sm text-[#13082a] dark:text-white font-black uppercase tracking-tight transition-all disabled:opacity-70 disabled:cursor-not-allowed" value={editForm.date_of_birth} onChange={(e) => setEditForm({ ...editForm, date_of_birth: e.target.value })} type="date" />
                                        ) : (
                                            <div className="w-full pl-14 pr-6 py-5 bg-slate-50 dark:bg-white/5 border border-transparent rounded-[1.5rem] text-sm text-[#13082a] dark:text-white font-black uppercase tracking-tight transition-all">
                                                {dob || "Not Set"}
                                            </div>
                                        )}
                                    </div>
                                </div>
                                <div className="space-y-4">
                                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] ml-2 leading-none">Age</label>
                                    <div className="relative group">
                                        <div className="w-full px-6 py-5 bg-slate-50 dark:bg-white/5 border border-transparent rounded-[1.5rem] text-sm text-[#13082a] dark:text-white font-black uppercase tracking-tight transition-all">
                                            {age !== null ? `${age} years` : "--"}
                                        </div>
                                    </div>
                                </div>

                                {/* Gender Selection Row */}
                                <div className="md:col-span-2 space-y-6 pt-4">
                                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] ml-2 leading-none">Gender Identity Identification</label>
                                    <div className="flex flex-wrap gap-8 p-6 bg-slate-50/50 dark:bg-white/5 rounded-[2rem] border border-slate-100 dark:border-white/5">
                                        {['Male', 'Female', 'Non-binary', 'Other / Prefer not to say'].map((opt) => {
                                            const val = opt.toLowerCase().split(' / ')[0].replace(' ', '-');
                                            const isActive = gender === val;
                                            return (
                                                <button
                                                    key={opt}
                                                    disabled={!isEditing}
                                                    onClick={() => setGender(val)}
                                                    className={`flex items-center gap-4 group/radio transition-all outline-none ${!isEditing ? 'opacity-70 cursor-not-allowed' : 'active:scale-95'}`}
                                                >
                                                    <div className={`size-6 rounded-full border-4 flex items-center justify-center transition-all ${isActive ? 'border-[#6143f4] bg-white' : 'border-slate-200 dark:border-slate-700 bg-transparent group-hover/radio:border-[#6143f4]/50'}`}>
                                                        {isActive && <span className="size-2 rounded-full bg-[#6143f4] block" />}
                                                    </div>
                                                    <span className={`text-xs uppercase tracking-widest leading-none mt-1 transition-all ${isActive ? 'text-[#13082a] dark:text-white font-black' : 'text-slate-400 dark:text-slate-500 font-bold group-hover/radio:text-[#6143f4]'}`}>{opt}</span>
                                                </button>
                                            );
                                        })}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default SettingsProfile;
