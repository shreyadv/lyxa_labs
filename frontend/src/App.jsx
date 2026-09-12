import { useEffect, useState } from 'react'
import { api } from './api'

function CapacityBar({ used, capacity }) {
  const pct = Math.min(100, (used / capacity) * 100)
  const danger = pct > 90
  return (
    <div className="capacity-bar">
      <div className="capacity-bar-track">
        <div
          className={`capacity-bar-fill ${danger ? 'danger' : ''}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="capacity-bar-label">
        {used}W used / {capacity}W ({capacity - used}W free)
      </div>
    </div>
  )
}

function ApplianceRow({ appliance, onToggle, onDelete }) {
  const stateClass = {
    running: 'state-running',
    off: 'state-off',
    shed: 'state-shed',
  }[appliance.state]

  return (
    <tr className={stateClass}>
      <td>{appliance.name}</td>
      <td>{appliance.wattage}W</td>
      <td>P{appliance.priority}</td>
      <td>
        <span className={`badge ${stateClass}`}>{appliance.state}</span>
      </td>
      <td>
        <button className="btn" onClick={() => onToggle(appliance)}>
          {appliance.state === 'off' ? 'Turn On' : 'Turn Off'}
        </button>
        <button className="btn danger" onClick={() => onDelete(appliance)}>
          Delete
        </button>
      </td>
    </tr>
  )
}

function ApplianceForm({ onCreate }) {
  const [name, setName] = useState('')
  const [wattage, setWattage] = useState('')
  const [priority, setPriority] = useState('')

  const submit = async (e) => {
    e.preventDefault()
    if (!name || !wattage || !priority) return
    await onCreate({ name, wattage: Number(wattage), priority: Number(priority) })
    setName('')
    setWattage('')
    setPriority('')
  }

  return (
    <form className="appliance-form" onSubmit={submit}>
      <input placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} />
      <input
        placeholder="Wattage"
        type="number"
        min="1"
        value={wattage}
        onChange={(e) => setWattage(e.target.value)}
      />
      <input
        placeholder="Priority (1 = most important)"
        type="number"
        min="1"
        value={priority}
        onChange={(e) => setPriority(e.target.value)}
      />
      <button className="btn primary" type="submit">
        Register Appliance
      </button>
    </form>
  )
}

export default function App() {
  const [status, setStatus] = useState(null)
  const [notice, setNotice] = useState(null)
  const [confirmDelete, setConfirmDelete] = useState(null)
  const [error, setError] = useState(null)

  const refresh = async () => {
    try {
      const data = await api.getStatus()
      setStatus(data)
    } catch (err) {
      setError(err.message)
    }
  }

  useEffect(() => {
    refresh()
  }, [])

  const showNotice = (message) => {
    setNotice(message)
    setTimeout(() => setNotice(null), 6000)
  }

  const handleCreate = async (appliance) => {
    try {
      await api.createAppliance(appliance)
      setError(null)
      await refresh()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleToggle = async (appliance) => {
    try {
      const action = appliance.state === 'off' ? api.turnOn : api.turnOff
      const result = await action(appliance.id)
      showNotice(result.message)
      setError(null)
      await refresh()
    } catch (err) {
      showNotice(err.message)
    }
  }

  const handleDelete = async (appliance) => {
    try {
      const result = await api.deleteAppliance(appliance.id)
      showNotice(result.message)
      setConfirmDelete(null)
      setError(null)
      await refresh()
    } catch (err) {
      setError(err.message)
    }
  }

  if (!status) {
    return (
      <div className="app">
        Loading...
        {error && <p className="error">{error}</p>}
      </div>
    )
  }

  return (
    <div className="app">
      <h1>Inverter Load Manager</h1>
      <CapacityBar used={status.current_load} capacity={status.capacity} />

      {notice && <div className="notice">{notice}</div>}
      {error && <div className="error">{error}</div>}

      <table className="appliance-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Wattage</th>
            <th>Priority</th>
            <th>State</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {status.appliances.map((a) => (
            <ApplianceRow
              key={a.id}
              appliance={a}
              onToggle={handleToggle}
              onDelete={(app) => setConfirmDelete(app)}
            />
          ))}
        </tbody>
      </table>

      <h2>Register New Appliance</h2>
      <ApplianceForm onCreate={handleCreate} />

      {confirmDelete && (
        <div className="modal-backdrop">
          <div className="modal">
            <p>Delete "{confirmDelete.name}"? This cannot be undone.</p>
            <button className="btn danger" onClick={() => handleDelete(confirmDelete)}>
              Yes, delete
            </button>
            <button className="btn" onClick={() => setConfirmDelete(null)}>
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  )
}