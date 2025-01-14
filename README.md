# uwo-fast.github.io

uwo-fast GitHub Pages website!

> 🌐 **Served fresh at:** [uwo-fast.github.io](https://uwo-fast.github.io/)

## Jekyll Development Primer

Useful one liner to fully clean and rebuild the site:

```
jekyll clean && bundle install && bundle exec jekyll build  # Bash
jekyll clean; bundle install; bundle exec jekyll build      # PowerShell
```

### Prerequisites

1. **Install Ruby**  
   Ensure you have Ruby installed on your system. Use [RubyInstaller](https://rubyinstaller.org/) for Windows or your package manager on macOS/Linux.

2. **Install Bundler**  
   Bundler manages Ruby gems and dependencies.

   ```
   gem install bundler
   ```

3. **Install Jekyll**  
   Install Jekyll globally (optional if using Bundler to manage dependencies).
   ```
   gem install jekyll
   ```

### Installation

1. **Clone the Repository**

   ```
   git clone https://github.com/uwo-fast/uwo-fast.github.io.git
   cd uwo-fast.github.io
   ```

2. **Install Dependencies**
   Use Bundler to install all required gems.
   ```
   bundle install
   ```

### Building the Site Locally

1. **Serve the Site**
   Start the local development server:

   ```
   bundle exec jekyll serve
   ```

2. **Access the Site**  
   Once the server starts, the local development address will be printed in the console (e.g., `http://127.0.0.1:4000` or `http://localhost:4000`).  
   Open this address in your browser to view the site.

### Cleaning the Environment

1. **Remove Generated Files**
   Clean up previously built site files.

   ```
   jekyll clean
   ```

2. **Reinstall Dependencies**
   If you suspect dependency issues, remove the `Gemfile.lock` and reinstall:

   ```
   rm Gemfile.lock
   bundle install
   ```

3. **Update Submodules** (if your site uses Git submodules):
   ```
   git submodule update --init --recursive
   ```

## Western University Brand Colors

### Primary Colors

- **Western Purple**

  - **Print PMS**: 268 C
  - **Print CMYK**: 82, 100, 0, 12
  - **Digital RGB**: 79, 38, 131
  - **Web Hex**: `#4F2683`

- **White**
  - **Print PMS**: N/A
  - **Print CMYK**: 0, 0, 0, 0
  - **Digital RGB**: 255, 255, 255
  - **Web Hex**: `#FFFFFF`

### Secondary Colors

- **Orchid**

  - **Print PMS**: 265 C
  - **Print CMYK**: N/A
  - **Digital RGB**: 154, 100, 246
  - **Web Hex**: `#8F55E0`

- **Deep Focus**

  - **Print PMS**: 275 C
  - **Print CMYK**: 85, 90, 45, 60
  - **Digital RGB**: 32, 20, 54
  - **Web Hex**: `#201436`

- **Black**

  - **Print PMS**: BLACK 6C
  - **Print CMYK**: 0, 0, 0, 100
  - **Digital RGB**: 0, 0, 0
  - **Web Hex**: `#000000`

- **Grey**
  - **Print PMS**: COOL GRAY 6C
  - **Print CMYK**: 0, 0, 0, 60
  - **Digital RGB**: 129, 130, 132
  - **Web Hex**: `#818284`

### Accent Colors

- **Sky**

  - **Print CMYK**: 40, 0, 0, 0
  - **Digital RGB**: 125, 234, 250
  - **Web Hex**: `#7DEAFB`

- **Spring**

  - **Print CMYK**: 40, 0, 80, 0
  - **Digital RGB**: 185, 248, 118
  - **Web Hex**: `#B9F876`

- **Vivid**

  - **Print CMYK**: 5, 0, 75, 0
  - **Digital RGB**: 252, 240, 94
  - **Web Hex**: `#FCF05E`

- **Tiger**
  - **Print CMYK**: 0, 20, 80, 0
  - **Digital RGB**: 240, 167, 87
  - **Web Hex**: `#F0A757`
