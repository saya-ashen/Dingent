import type { ReactNode } from 'react';
import clsx from 'clsx';
import Heading from '@theme/Heading';
import styles from './styles.module.css';

type FeatureItem = {
    title: string;
    Svg: React.ComponentType<React.ComponentProps<'svg'>>;
    description: ReactNode;
};

const FeatureList: FeatureItem[] = [
  {
    title: 'No More Repetition',
    Svg: require('@site/static/img/undraw_docusaurus_mountain.svg').default,
    description: (
      <>
        Best practices for backend (LangGraph), data interfaces (Plugin System),
        chat UI (CopilotKit), and a full-featured admin dashboard are all packaged together.
        Skip the boilerplate and build your business logic right away.
      </>
    ),
  },
  {
    title: 'Visual Configuration',
    Svg: require('@site/static/img/undraw_docusaurus_tree.svg').default,
    description: (
      <>
        Manage assistants, workflows, and settings through an integrated admin
        dashboard—no more manual config file editing or tedious setup.
      </>
    ),
  },
  {
    // --- THIS IS THE UPDATED FEATURE ---
    title: 'Extensible & Versatile',
    Svg: require('@site/static/img/undraw_docusaurus_react.svg').default,
    description: (
      <>
        With a modular architecture and a powerful plugin system, Dingent grows with
        your needs. Build anything from simple task automators to complex, multi-agent
        systems, all on one solid foundation.
      </>
    ),
  },
];

function Feature({ title, Svg, description }: FeatureItem) {
    return (
        <div className={clsx('col col--4')}>
            <div className="text--center">
                <Svg className={styles.featureSvg} role="img" />
            </div>
            <div className="text--center padding-horiz--md">
                <Heading as="h3">{title}</Heading>
                <p>{description}</p>
            </div>
        </div>
    );
}

export default function HomepageFeatures(): ReactNode {
    return (
        <section className={styles.features}>
            <div className="container">
                <div className="row">
                    {FeatureList.map((props, idx) => (
                        <Feature key={idx} {...props} />
                    ))}
                </div>
            </div>
        </section>
    );
}
