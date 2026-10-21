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
import { PlanningTasksPage, PreviewPage } from "../features/product/tasks";
import { SavedPage } from "../features/product/SavedPage";

export const routes: RouteObject[] = [
  {
    element: <ProductLayout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: "plan", element: <BriefPage /> },
      { path: "login", element: <AuthPage /> },
      { path: "trips", element: <LibraryPage /> },
      { path: "trips/:tripId", element: <SavedPage /> },
      { path: "account", element: <AccountPage /> },
      { path: "examples/:exampleId", element: <ExamplePage /> },
      { path: "planning", element: <PlanningTasksPage /> },
      { path: "planning/:taskId", element: <PlanningTasksPage /> },
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
