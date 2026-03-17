// BaseCollector abstract class — Strategy pattern
// All collectors extend this and implement collect() and isSupported()

class BaseCollector {
  constructor() {
    this.name = '';       // unique collector identifier
    this.category = '';   // 'cyber' | 'ai'
    this.platforms = [];  // ['linux', 'darwin', 'win32']
  }

  async collect(context) {
    // Returns: Evidence[]
    throw new Error(`${this.constructor.name}.collect() not implemented`);
  }

  isSupported() {
    // Returns: boolean — OS platform check
    return this.platforms.includes(process.platform);
  }
}

module.exports = BaseCollector;
