import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import Topbar from './Topbar'
import MobileNav from './MobileNav'

export default function Layout() {
  return (
    <div className="flex min-h-screen bg-bg-base">
      <Sidebar />
      <div className="flex-1 min-w-0 flex flex-col pb-16 md:pb-0">
        <Topbar />
        <main className="flex-1 px-4 md:px-6 py-6 max-w-[1600px] w-full mx-auto">
          <Outlet />
        </main>
      </div>
      <MobileNav />
    </div>
  )
}
