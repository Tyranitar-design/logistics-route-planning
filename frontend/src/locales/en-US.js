export default {
  // Common
  common: {
    confirm: 'Confirm',
    cancel: 'Cancel',
    save: 'Save',
    delete: 'Delete',
    edit: 'Edit',
    add: 'Add',
    search: 'Search',
    reset: 'Reset',
    export: 'Export',
    import: 'Import',
    refresh: 'Refresh',
    loading: 'Loading...',
    success: 'Success',
    error: 'Error',
    warning: 'Warning',
    tip: 'Tip',
    all: 'All',
    status: 'Status',
    action: 'Action',
    createTime: 'Create Time',
    updateTime: 'Update Time',
    description: 'Description',
    remark: 'Remark',
    detail: 'Detail'
  },
  
  // Navigation Menu
  menu: {
    dashboard: 'Dashboard',
    map: 'Map View',
    earth3d: '3D Earth',
    dataScreen: 'Data Screen',
    nodes: 'Nodes',
    routes: 'Routes',
    orders: 'Orders',
    dispatch: 'Smart Dispatch',
    advanced: 'Advanced',
    tracking: 'Tracking',
    multiObjective: 'Multi-Objective',
    agile: 'Agile Optimization',
    risk: 'Risk Management',
    alert: 'Alert Center',
    analytics: 'Analytics',
    cost: 'Cost Analysis',
    mlPrediction: 'AI Prediction',
    anomaly: 'Anomaly Detection',
    dataAnalytics: 'Data Analytics',
    auditLog: 'Audit Log',
    supplier: 'Supplier',
    vehicles: 'Vehicles',
    users: 'Users',
    testData: 'Test Data',
    settings: 'Settings'
  },
  
  // Orders
  order: {
    title: 'Order Management',
    orderNumber: 'Order No.',
    origin: 'Origin',
    destination: 'Destination',
    cargo: 'Cargo',
    weight: 'Weight(kg)',
    volume: 'Volume(m³)',
    sender: 'Sender',
    receiver: 'Receiver',
    priority: 'Priority',
    status: {
      pending: 'Pending',
      assigned: 'Assigned',
      in_transit: 'In Transit',
      delivered: 'Delivered',
      cancelled: 'Cancelled'
    }
  },
  
  // Vehicles
  vehicle: {
    title: 'Vehicle Management',
    plateNumber: 'Plate Number',
    vehicleType: 'Vehicle Type',
    brand: 'Brand',
    model: 'Model',
    loadCapacity: 'Load Capacity(t)',
    driver: 'Driver',
    status: {
      available: 'Available',
      in_use: 'In Use',
      maintenance: 'Maintenance',
      offline: 'Offline'
    }
  },
  
  // Routes
  route: {
    title: 'Route Management',
    routeName: 'Route Name',
    startNode: 'Start Node',
    endNode: 'End Node',
    distance: 'Distance(km)',
    duration: 'Duration(h)',
    tollCost: 'Toll Cost(¥)',
    fuelCost: 'Fuel Cost(¥)',
    totalCost: 'Total Cost(¥)',
    recommend: 'Route Recommend',
    optimize: 'Route Optimize'
  },
  
  // Analytics
  analytics: {
    title: 'Data Analytics',
    overview: 'Overview',
    trend: 'Trend',
    distribution: 'Distribution',
    comparison: 'Comparison',
    export: 'Export Report',
    totalOrders: 'Total Orders',
    totalVehicles: 'Total Vehicles',
    totalRoutes: 'Total Routes',
    totalCost: 'Total Cost',
    avgCost: 'Avg Cost',
    savingRate: 'Saving Rate'
  },
  
  // Alerts
  alert: {
    title: 'Alert Center',
    orderAlert: 'Order Alert',
    vehicleAlert: 'Vehicle Alert',
    routeAlert: 'Route Alert',
    supplyChainAlert: 'Supply Chain Alert',
    healthScore: 'Health Score',
    viewAll: 'View All'
  },
  
  // Login
  login: {
    title: 'Logistics Route Planning System',
    username: 'Username',
    password: 'Password',
    rememberMe: 'Remember Me',
    submit: 'Login',
    forgotPassword: 'Forgot Password?',
    register: 'Register'
  },
  
  // User
  user: {
    profile: 'Profile',
    logout: 'Logout',
    changePassword: 'Change Password',
    role: {
      admin: 'Admin',
      user: 'User',
      driver: 'Driver'
    }
  }
}
