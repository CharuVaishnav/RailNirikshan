// Small pieces shared by the officer and staff screens.
import { useEffect, useRef, useState } from "react";
import { shrinkPhoto } from "../../device.js";

export function ScreenHead({ title, sub, onBack }) {
  return (
    <div className="screen-head">
      {onBack && (
        <button type="button" className="btn btn-quiet" onClick={onBack}>
          Back
        </button>
      )}
      <h1>{title}</h1>
      {sub && <p>{sub}</p>}
    </div>
  );
}

// On a phone this opens the camera; on a laptop it opens the file chooser.
export function PhotoPicker({ file, onChange, label = "Add photo" }) {
  const input = useRef(null);
  const [preview, setPreview] = useState(null);

  useEffect(() => {
    if (!file) {
      setPreview(null);
      return undefined;
    }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  async function picked(e) {
    const chosen = e.target.files[0];
    e.target.value = ""; // lets the same photo be chosen again
    onChange(chosen ? await shrinkPhoto(chosen) : null);
  }

  return (
    <div className="picker">
      <input ref={input} type="file" accept="image/*" capture="environment" hidden onChange={picked} />
      {preview && <img className="picker-preview" src={preview} alt="Chosen photo" />}
      <button type="button" className="btn btn-plain" onClick={() => input.current.click()}>
        {file ? "Change photo" : label}
      </button>
      {file && (
        <button type="button" className="btn btn-quiet" onClick={() => onChange(null)}>
          Remove
        </button>
      )}
    </div>
  );
}

// One line that says whether a GPS position will be attached.
export function GpsLine({ position, missingNote }) {
  const tone = { finding: "idle", ok: "clear", none: "caution" }[position.status];
  return (
    <p className="gps">
      <span className={`lamp lamp-${tone}`} aria-hidden="true" />
      {position.status === "finding" && "Finding your location"}
      {position.status === "ok" && "Your location will be attached"}
      {position.status === "none" && (
        <>
          <span>Location not available. {missingNote}</span>
          <button type="button" className="btn btn-quiet" onClick={position.retry}>
            Try again
          </button>
        </>
      )}
    </p>
  );
}
