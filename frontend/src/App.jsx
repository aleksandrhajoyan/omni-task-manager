import React, { useState, useEffect } from 'react';
import axios from 'axios';

function App() {
  const [tasks, setTasks] = useState([]);
  const [wsStatus, setWsStatus] = useState('Connecting...');

  // 1. Загрузка существующих задач по HTTP при старте
  useEffect(() => {
    axios.get('http://localhost:8000/tasks')
      .then(response => {
        setTasks(response.data);
      })
      .catch(error => {
        console.error("Ошибка при загрузке задач:", error);
      });
  }, []);

  // 2. Подключение WebSocket и обработка событий в реальном времени
  useEffect(() => {
    const socket = new WebSocket('ws://localhost:8000/ws');

    socket.onopen = () => setWsStatus('Connected ✅');
    socket.onclose = () => setWsStatus('Disconnected ❌');
    socket.onerror = (error) => console.error('Ошибка WS:', error);

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('Получено событие по WS:', data);
      
      if (data.event === 'task_created' && data.task) {
        // Добавляем новую задачу вверх списка
        setTasks((prevTasks) => [data.task, ...prevTasks]);
      } 
      else if (data.event === 'task_updated' && data.task) {
        // Находим измененную задачу и обновляем её состояние
        setTasks((prevTasks) => prevTasks.map(t => t.id === data.task.id ? data.task : t));
      } 
      else if (data.event === 'task_deleted' && data.task_id) {
        // Удаляем задачу из списка на экране
        setTasks((prevTasks) => prevTasks.filter(t => t.id !== data.task_id));
      }
    };

    return () => socket.close();
  }, []);

  // Функция изменения статуса задачи через HTTP PUT
  const changeStatus = (taskId, newStatus) => {
    axios.put(`http://localhost:8000/tasks/${taskId}`, { status: newStatus })
      .catch(err => console.error("Ошибка изменения статуса:", err));
  };

  // Функция удаления задачи через HTTP DELETE
  const deleteTask = (taskId) => {
    if (window.confirm("Удалить эту задачу?")) {
      axios.delete(`http://localhost:8000/tasks/${taskId}`)
        .catch(err => console.error("Ошибка при удалении:", err));
    }
  };

  return (
    <div style={{ padding: '20px', fontFamily: 'Arial, sans-serif', maxWidth: '800px', margin: '0 auto' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '2px solid #eee', paddingBottom: '10px' }}>
        <h2>🚀 Omni Task Manager Dashboard</h2>
        <span style={{ 
          padding: '5px 10px', 
          borderRadius: '15px', 
          backgroundColor: wsStatus.includes('✅') ? '#e6f4ea' : '#fce8e6',
          color: wsStatus.includes('✅') ? '#137333' : '#c5221f',
          fontSize: '14px',
          fontWeight: 'bold'
        }}>
          WS: {wsStatus}
        </span>
      </header>

      <main style={{ marginTop: '20px' }}>
        <h3>Список задач</h3>
        {tasks.length === 0 ? (
          <p style={{ color: '#666', fontStyle: 'italic' }}>Задач пока нет. Отправьте сообщение боту!</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {tasks.map((task) => (
              <div key={task.id} style={{ 
                padding: '15px', 
                border: '1px solid #ddd', 
                borderRadius: '8px',
                backgroundColor: '#fff',
                boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}>
                <div>
                  <strong style={{ fontSize: '16px' }}>{task.title}</strong>
                  <div style={{ fontSize: '12px', color: '#666', marginTop: '5px' }}>
                    User ID: {task.telegram_user_id} | Статус: <span style={{ fontWeight: 'bold' }}>{task.status}</span>
                  </div>
                </div>

                {/* Блок интерактивных кнопок */}
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  {task.status !== 'in_progress' && task.status !== 'completed' && (
                    <button 
                      onClick={() => changeStatus(task.id, 'in_progress')}
                      style={{ padding: '6px 10px', backgroundColor: '#e8f0fe', color: '#1a73e8', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}
                    >
                      В процессе
                    </button>
                  )}
                  {task.status !== 'completed' && (
                    <button 
                      onClick={() => changeStatus(task.id, 'completed')}
                      style={{ padding: '6px 10px', backgroundColor: '#e6f4ea', color: '#137333', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}
                    >
                      Выполнено
                    </button>
                  )}
                  <button 
                    onClick={() => deleteTask(task.id)}
                    style={{ padding: '6px 10px', backgroundColor: '#fce8e6', color: '#c5221f', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}
                  >
                    🗑
                  </button>
                </div>

              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;