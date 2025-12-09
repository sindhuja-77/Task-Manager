import React, { useState } from 'react';
import TaskForm from './components/TaskForm';
import TaskList from './components/TaskList';
import GenerateTaskForm from './components/GeneratedTasksForm';
import Recommendations from './components/Recommendations';
import './App.css';

const App = () => {
  const [refresh, setRefresh] = useState(false);
  const [recommendation, setRecommendation] = useState('');
  const [loading, setLoading] = useState(false);

  const triggerRefresh = () => setRefresh(!refresh);

  const fetchRecommendations = async () => {
    setLoading(true);
    try {
      const res = await fetch('http://127.0.0.1:8000/recommendations');
      const data = await res.json();
      setRecommendation(data.recommendation || 'No  tasks to provide recommendations.');
    } catch (error) {
      console.error('Error fetching recommendations:', error);
      setRecommendation('Failed to fetch recommendations.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1>📝 Task Manager App</h1>

      <TaskForm fetchTasks={triggerRefresh} />
      <GenerateTaskForm fetchTasks={triggerRefresh} />
      
      <TaskList 
        refresh={refresh} 
        fetchRecommendations={fetchRecommendations} 
      />

      <Recommendations
        recommendation={recommendation}
        fetchRecommendations={fetchRecommendations}
        loading={loading}
      />
    </div>
  );
};

export default App;
