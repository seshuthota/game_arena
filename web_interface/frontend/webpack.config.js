const path = require('path');
const webpack = require('webpack');

module.exports = {
  mode: process.env.NODE_ENV || 'development',
  
  // Bundle optimization for chess libraries
  optimization: {
    splitChunks: {
      chunks: 'all',
      cacheGroups: {
        // Separate chess engine libraries into their own bundle
        chess: {
          name: 'chess',
          test: /[\\/]node_modules[\\/](chess\.js|@chrisoakman[\\/]chessboardjs|jquery)[\\/]/,
          priority: 30,
          chunks: 'all',
        },
        // Separate React and core libraries
        vendor: {
          name: 'vendor',
          test: /[\\/]node_modules[\\/](react|react-dom|react-router-dom)[\\/]/,
          priority: 20,
          chunks: 'all',
        },
        // UI component libraries
        ui: {
          name: 'ui',
          test: /[\\/]node_modules[\\/](lucide-react|recharts|react-window)[\\/]/,
          priority: 15,
          chunks: 'all',
        },
        // Default vendor chunk
        default: {
          name: 'common',
          minChunks: 2,
          priority: 10,
          reuseExistingChunk: true,
        },
      },
    },
    
    // Tree shaking and dead code elimination
    usedExports: true,
    providedExports: true,
    sideEffects: false,
    
    // Minimize bundle size
    minimize: process.env.NODE_ENV === 'production',
  },
  
  resolve: {
    // Optimize module resolution
    alias: {
      '@': path.resolve(__dirname, 'src'),
      'components': path.resolve(__dirname, 'src/components'),
      'utils': path.resolve(__dirname, 'src/utils'),
      'hooks': path.resolve(__dirname, 'src/hooks'),
      'types': path.resolve(__dirname, 'src/types'),
    },
    
    // Prefer ES modules for better tree shaking
    mainFields: ['module', 'main'],
    
    // Cache module resolution for faster builds
    cache: true,
  },
  
  plugins: [
    // Define environment variables
    new webpack.DefinePlugin({
      'process.env.REACT_APP_BUILD_DATE': JSON.stringify(new Date().toISOString()),
      'process.env.REACT_APP_VERSION': JSON.stringify(process.env.npm_package_version),
    }),
    
    // Analyze bundle size in production
    ...(process.env.ANALYZE_BUNDLE ? [
      new (require('webpack-bundle-analyzer')).BundleAnalyzerPlugin({
        analyzerMode: 'static',
        openAnalyzer: false,
        reportFilename: 'bundle-report.html',
      })
    ] : []),
  ],
  
  // Performance hints for large bundles
  performance: {
    hints: process.env.NODE_ENV === 'production' ? 'warning' : false,
    maxEntrypointSize: 500000, // 500KB
    maxAssetSize: 300000,      // 300KB
    assetFilter: (assetFilename) => {
      // Only check JS bundles, not images or other assets
      return assetFilename.endsWith('.js');
    },
  },
  
  // Development optimizations
  ...(process.env.NODE_ENV === 'development' && {
    devtool: 'eval-cheap-module-source-map',
    cache: {
      type: 'filesystem',
      buildDependencies: {
        config: [__filename],
      },
    },
  }),
};