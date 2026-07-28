import { useRef, useState } from "react";
import { Camera, X } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import ProfilePhoto from "@/components/ProfilePhoto";

export default function ProfilePanel({ profile, user, onClose, onUploaded }) {
  const inputRef = useRef(null);
  const [uploading, setUploading] = useState(false);
  const employee = profile?.employee;

  const uploadPhoto = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    if (!file.type.match(/^image\/(jpeg|png|webp)$/) || file.size > 5 * 1024 * 1024) {
      toast.error("Use a JPG, PNG, or WebP photo under 5 MB");
      return;
    }
    const body = new FormData();
    body.append("file", file);
    setUploading(true);
    try {
      await api.post("/profile/photo", body);
      toast.success("Profile photo updated");
      onUploaded();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Could not upload your photo");
    } finally {
      setUploading(false);
    }
  };

  return <section className="profile-popover" data-testid="profile-panel"><button aria-label="Close profile" className="icon-button profile-close" data-testid="profile-close-button" onClick={onClose}><X size={18} /></button><div className="profile-photo-area"><ProfilePhoto fileId={employee?.photo_file_id} name={user.name} /><div><p className="eyebrow">MY PROFILE</p><h2 data-testid="profile-name">{user.name}</h2><p data-testid="profile-role">{user.role === "admin" ? "Administrator account" : employee?.territory}</p></div></div><p data-testid="profile-phone">{user.phone}</p>{user.role === "employee" && <><input accept="image/jpeg,image/png,image/webp" className="visually-hidden" data-testid="profile-photo-input" ref={inputRef} type="file" onChange={uploadPhoto} /><button className="outline-button profile-upload-button" data-testid="profile-photo-upload-button" disabled={uploading} onClick={() => inputRef.current?.click()}><Camera size={16} />{uploading ? "Uploading…" : "Update photo"}</button></>}</section>;
}