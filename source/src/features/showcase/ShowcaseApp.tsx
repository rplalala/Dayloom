import { useEffect, useState } from 'react';
import { Link, NavLink, Outlet, useLocation, useParams, type RouteObject } from 'react-router-dom';
import { HomeContent } from '../../routes/product/HomePage';
import { ExampleCollection } from '../product/detail/ExampleCards';
import { exampleCover, examplePhotos } from '../product/detail/exampleMedia';
import { TripDetail } from '../product/detail/TripDetail';
import type { ExampleCard, ProductDetail } from '../product/detail/types';
import { Icon } from '../product/Icon';
import '../../styles/dayloom.css';
import '../product/library.css';
import './showcase.css';

const repository = 'https://github.com/rplalala/Dayloom';

function ShowcaseLayout() {
  const [mobile, setMobile] = useState(false);
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo?.(0, 0);
  }, [pathname]);
  const navigation = <>
    <NavLink className={({ isActive }) => `nav-link ${isActive ? 'selected' : ''}`} to="/" end>Home</NavLink>
    <NavLink className={({ isActive }) => `nav-link ${isActive || pathname.startsWith('/examples/') ? 'selected' : ''}`} to="/trips">Examples</NavLink>
    <NavLink className={({ isActive }) => `nav-link ${isActive ? 'selected' : ''}`} to="/about">About Dayloom</NavLink>
  </>;
  return <div className="dayloom">
    <header className="site-header"><div className="container nav-inner">
      <Link className="brand" to="/" aria-label="Dayloom home"><span className="brand-symbol"><Icon name="spark" size={21} /></span><span className="brand-name">Dayloom</span></Link>
      <nav className="site-nav" aria-label="Main navigation">{navigation}</nav>
      <div className="nav-actions"><a className="btn btn-quiet btn-small" href={repository}>View project <Icon name="arrow" size={16} /></a>
        <button type="button" className="mobile-toggle" aria-label="Open navigation" aria-expanded={mobile} aria-controls="showcase-mobile-nav" onClick={() => setMobile(!mobile)}><Icon name="menu" size={23} /></button>
      </div>
    </div>{mobile && <nav id="showcase-mobile-nav" className="mobile-panel" aria-label="Mobile navigation" onClick={() => setMobile(false)}>{navigation}</nav>}</header>
    <div className="showcase-banner"><div className="container">Public showcase · Explore example itineraries. <Link to="/about">About the full application <Icon name="arrow" size={14} /></Link></div></div>
    <main id="main-content"><Outlet /></main>
    <footer className="site-footer"><div className="container footer-flex"><div><div className="footer-brand"><Icon name="spark" size={21} /> Dayloom</div><p>Make room for the places that move you.</p></div><div className="footer-links"><Link to="/">Home</Link><Link to="/trips">Examples</Link><Link to="/about">About Dayloom</Link><a href={repository}>GitHub</a></div></div>
      <div className="container footer-note">Historical example itineraries. Confirm opening times, prices, weather and bookings before you travel.</div>
    </footer>
  </div>;
}

function AboutPage() {
  return <div className="page container showcase-about">
    <div className="page-heading"><span className="eyebrow">YOUR JOURNEY, YOUR WAY</span><h1>Meet Dayloom.</h1><p>A destination, a few ideas, a rhythm that feels like you. Bring your days together in one clear itinerary.</p></div>
    <div className="intro-rail">
      <div><Icon name="calendar" size={24} /><div><strong>Start with your travel ideas</strong><p>Choose your destination, dates, budget and interests in the full application.</p></div></div>
      <div><Icon name="route" size={24} /><div><strong>See your days come together</strong><p>Explore daily visits, travel connections, weather and optional nearby discoveries.</p></div></div>
      <div><Icon name="checklist" size={24} /><div><strong>Keep what matters</strong><p>Review a generated itinerary, save it to your library, and return to your travel briefs.</p></div></div>
    </div>
    <section className="section"><div className="section-heading"><div><span className="eyebrow">EXPLORE AT YOUR OWN PACE</span><h2>A glimpse of the journey.</h2></div></div>
      <p>This public showcase lets you browse two historical example itineraries, open place details and inspect photo sources. Example dates, weather and travel estimates describe those saved plans.</p>
      <p>Creating an account, generating a new itinerary and saving personal trips are available in a separately installed Dayloom application. Those services are not connected to this showcase.</p>
      <div className="hero-actions"><Link className="btn btn-primary" to="/trips">Explore the examples <Icon name="arrow" size={17} /></Link><a className="btn btn-light" href={`${repository}#readme`}>Get the full application <Icon name="arrow" size={17} /></a></div>
    </section>
  </div>;
}

function ShowcaseExample({ details }: { details: ProductDetail[] }) {
  const { exampleId } = useParams();
  const detail = details.find(item => item.id === exampleId);
  if (!detail) return <ShowcaseNotFound />;
  return <TripDetail key={detail.id} detail={detail} staticMedia={examplePhotos(detail.id)} coverMedia={exampleCover(detail.id)} backLink={{ to: '/trips', label: 'Back to examples' }} />;
}

function ShowcaseNotFound() {
  return <div className="page container"><h1>Page not found.</h1><p>This page is not part of the public showcase.</p><Link className="btn btn-primary" to="/trips">Browse examples</Link></div>;
}

export function showcaseRoutes(details: (ProductDetail & { created_at?: string })[]): RouteObject[] {
  const cards: ExampleCard[] = details.map(detail => ({
    id: detail.id, title: detail.title, destination: detail.destination,
    created_at: detail.created_at,
    start_date: detail.start_date, end_date: detail.end_date, description: detail.description,
    illustration_key: detail.illustration_key, day_count: detail.days.length,
    stop_count: detail.days.reduce((count, day) => count + day.activities.filter(activity => activity.time_use !== 'free_window').length, 0),
    transfer_count: detail.transfers.length,
  }));
  return [{ element: <ShowcaseLayout />, children: [
    { index: true, element: <HomeContent /> },
    { path: 'trips', element: <div className="page container trips-page"><div className="page-heading"><span className="eyebrow">A LITTLE INSPIRATION</span><h1>Example itineraries</h1><p>Explore a few days in Sydney and London, with the details together.</p></div><ExampleCollection cards={cards} /></div> },
    { path: 'examples/:exampleId', element: <ShowcaseExample details={details} /> },
    { path: 'about', element: <AboutPage /> },
    { path: '*', element: <ShowcaseNotFound /> },
  ] }];
}
