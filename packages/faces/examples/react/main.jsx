// Vite + React: `npm install && npm run dev`.
import { useState } from "react";
import { createRoot } from "react-dom/client";
import { FamilyFace } from "kinfaces/react";
import { familyTree, flattenTree, inheritedChange } from "kinfaces";
import "kinfaces/faces.css"; // optional: breathing and blinking, off under reduced motion

function App() {
  const [family, setFamily] = useState("ada");
  const people = flattenTree(familyTree(family, 4, 2));
  return (
    <main style={{ font: "16px/1.5 system-ui", maxWidth: 640, margin: "2rem auto", padding: "0 16px" }}>
      <h1>Family of {family}</h1>
      <label>
        Family name <input value={family} onChange={(e) => setFamily(e.target.value)} />
      </label>
      <ul style={{ display: "flex", flexWrap: "wrap", gap: 12, padding: 0, listStyle: "none" }}>
        {people.map((p) => (
          <li key={p.id} style={{ textAlign: "center", fontSize: 12 }}>
            {/* title makes it an image with a name; the visible id below is the caption */}
            <FamilyFace traits={p.traits} life="alive" size={56} background="#0A0E17" title={`${family}, person ${p.id}, generation ${p.gen}`} />
            <div>{p.id}</div>
          </li>
        ))}
      </ul>
      <p>Generation 5 of this family got {inheritedChange(5, family)}.</p>
      {/* the pointer-following variant */}
      <FamilyFace gen={3} family={family} life="alive" track size={96} background="#0A0E17" title="Move the pointer" />
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
