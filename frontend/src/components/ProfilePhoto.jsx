import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function ProfilePhoto({ fileId, name, className = "profile-avatar" }) {
  const [source, setSource] = useState("");

  useEffect(() => {
    let imageUrl = "";
    if (!fileId) {
      setSource("");
      return undefined;
    }
    api.get(`/files/${fileId}`, { responseType: "blob" }).then(({ data }) => {
      imageUrl = URL.createObjectURL(data);
      setSource(imageUrl);
    }).catch(() => setSource(""));
    return () => { if (imageUrl) URL.revokeObjectURL(imageUrl); };
  }, [fileId]);

  if (source) return <img alt={`${name}'s profile`} className={className} data-testid={`profile-photo-${fileId}`} src={source} />;
  return <span className={`${className} profile-avatar-fallback`} data-testid={`profile-photo-fallback-${name}`}>{name?.[0] || "?"}</span>;
}