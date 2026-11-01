import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { createHashRouter, RouterProvider } from 'react-router-dom';
import details from '../../../data/examples.json';
import type { ProductDetail } from '../product/detail/types';
import { showcaseRoutes } from './ShowcaseApp';
import '../../styles/global.css';

const root = document.getElementById('root');
if (!root) throw new Error('Application root element was not found');

createRoot(root).render(<StrictMode><RouterProvider router={createHashRouter(showcaseRoutes(details as ProductDetail[]))} /></StrictMode>);
