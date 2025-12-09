import React from 'react';

const Recommendations = ({ recommendation, fetchRecommendations, loading }) => {
  return (
    <div>
      <h2>AI Recommendations</h2>
      <button onClick={fetchRecommendations} disabled={loading}>
        {loading ? 'Fetching...' : 'Get Recommendation'}
      </button>
      {recommendation && (
  <div className="recommendation-box">
    {recommendation.split('\n').map((line, index) => {
      const cleanedLine = line.replace(/\*\*/g, "").replace(/^- /, "• ");
      return <p key={index}>{cleanedLine}</p>;
    })}
  </div>
)}
    </div>
  );
};

export default Recommendations;
