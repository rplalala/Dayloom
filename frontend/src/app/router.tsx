import { type RouteObject, createBrowserRouter } from "react-router-dom";

import { DeveloperLayout } from "../layouts/DeveloperLayout";
import { ProductLayout } from "../layouts/ProductLayout";
import { DeveloperPlannerPage } from "../routes/developer/DeveloperPlannerPage";
import { NotFoundPage } from "../routes/NotFoundPage";
import { HomePage } from "../routes/product/HomePage";
import { BriefPage } from "../features/product/BriefPage";
import { AuthPage } from "../features/product/AuthPage";
import { LibraryPage } from "../features/product/LibraryPage";
import { AccountPage } from "../features/product/AccountPage";
import { ExamplePage } from "../features/product/detail/ExamplePage";
import { LegacyPlanningRedirect, PreviewPage } from "../features/product/tasks";
import { SavedPage } from "../features/product/SavedPage";
import { DraftDetailPage } from "../features/product/DraftDetailPage";
import { ImportPage } from '../features/product/ImportPage';
import { CopyRecoveryPage } from '../features/product/CopyRecoveryPage';

export const routes: RouteObject[] = [
  { path: 'config', lazy: async () => {
    const { ConfigurationPage } = await import('../features/configuration/ConfigurationPage');
    return { Component: ConfigurationPage };
  } },
  {
    element: <ProductLayout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: "plan", element: <BriefPage /> },
      { path: "login", element: <AuthPage /> },
      { path: "trips", element: <LibraryPage /> },
      { path: "import", element: <ImportPage /> },
      { path: "copy-recovery", element: <CopyRecoveryPage /> },
      { path: "trips/:tripId", element: <SavedPage /> },
      { path: "drafts/:draftId", element: <DraftDetailPage /> },
      { path: "account", element: <AccountPage /> },
      { path: "examples/:exampleId", element: <ExamplePage /> },
      { path: "planning", element: <LegacyPlanningRedirect /> },
      { path: "planning/:taskId", element: <LegacyPlanningRedirect /> },
      { path: "previews/:previewId", element: <PreviewPage /> },
    ],
  },
  {
    path: "dev",
    element: <DeveloperLayout />,
    children: [
      { index: true, element: <DeveloperPlannerPage /> },
    ],
  },
  { path: "*", element: <NotFoundPage /> },
];

export const router = createBrowserRouter(routes);
