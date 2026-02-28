"use client";

import dynamic from "next/dynamic";

const SchoolMap = dynamic(() => import("@/components/maps/SchoolMap"), {
  ssr: false,
  loading: () => (
    <div className="panel">
      <div className="panel-header"><h2>Stadium Map</h2></div>
      <div style={{ padding: "20px", textAlign: "center", color: "#666" }}>Loading map...</div>
    </div>
  ),
});

export default SchoolMap;
