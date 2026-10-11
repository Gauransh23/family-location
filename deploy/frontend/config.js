window.owntracks = window.owntracks || {};
window.owntracks.config = {
  locale: "en-US",
  map: {
    url: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    attribution: "&copy; OpenStreetMap contributors",
    maxPointDistance: 1500,
  },
  onLocationChange: {
    fitView: false,
    reloadHistory: false,
  },
  showDistanceTravelled: true,
};
