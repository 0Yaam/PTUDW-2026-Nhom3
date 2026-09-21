# Small Kitchen UI theme

Visual reference: [Food Website Design by Azza khoffi](https://dribbble.com/shots/22211424-Food-Website-Design), selected by Han from three Dribbble shots. We reviewed [Maido](https://dribbble.com/shots/27591591-Maido-Restaurant-Website-Design) and [Culinary Website](https://dribbble.com/shots/22947267-Culinary-Website) as alternatives. The first concept fits a culinary blog's discovery and recipe content; Maido focuses on restaurant reservations, and the third on a restaurant menu.

## Implementation and provenance

The Dribbble shot is a design reference, not a downloadable application template or a code license. The UI is an original Next.js implementation. No Dribbble images, branding, source code, or scripts are copied into the project. Food photos in `frontend/public/images` were generated for this project. An earlier Bistro template was downloaded into the ignored `.template-audit/bistro` folder for comparison; no Bistro code or assets remain in the adapted UI.

The visual system uses a light canvas, warm pink accents, a central food collage, editorial headings, photographed category cards, and simple forms. Shared colors and typography are in `frontend/src/app/globals.css`. The header, footer, home, loading and error states, and Admin category page use the same design tokens. For future pages, reuse those tokens and the shared shell rather than copying the Dribbble composition into every screen.

## SRS and integration boundary

The home category cards read real category names, descriptions, recipe counts, and optional image URLs from `/api/v1/categories`. The category management forms still use the existing create/update API and Admin permission checks. The account form keeps the existing registration and login flow. The design adds no reservation, ordering, or recipe-detail behavior absent from the current SRS issue. Mobile layout, visible focus states, labels, landmarks, and reduced-motion styling support NFR-USE-001/002.

The locally generated photos are decorative previews when a category does not have an image URL. Prompts used: a Vietnamese phở and bánh mì editorial tabletop scene; an overhead breakfast of eggs and toast; an overhead vegetable and quinoa plate; and an overhead chocolate dessert. Each prompt requested no text, logos, people, or watermarks. Replace previews with project-owned media as recipe and category content grows.
